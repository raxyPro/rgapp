#
from flask import Flask, redirect, request
from config import Config
from extensions import db, login_manager
from flask_login import current_user

from models import RBModule, RBUserModule, RBUserProfile

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    #from routes_home import home_bp
    import routes_home
    #from routes_auth import auth_bp
    import routes_auth
    import routes_admin

    #from routes_admin import admin_bp
    import routes_user 

    app.register_blueprint(routes_home.home_bp)
    app.register_blueprint(routes_auth.auth_bp)
    #app.register_blueprint(admin_bp)
    app.register_blueprint(routes_admin.admin_bp)
    app.register_blueprint(routes_user.user_bp)

    @app.after_request
    def no_cache(response):
        """Prevent client/proxy caching of dynamic pages."""
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    subpath = (app.config.get("APP_SUBPATH") or "").strip("/")
    if subpath:
        prefix = f"/{subpath}"

        @app.before_request
        def _redirect_subpath():
            # Keep requests under the configured subpath; redirect absolute root paths.
            if request.path == prefix or request.path.startswith(prefix + "/"):
                return
            # Allow static files without redirect to avoid loops if served by web server directly.
            if request.path.startswith("/static/"):
                return
            return redirect(f"{prefix}{request.path}", code=302)
    
    @app.context_processor
    def inject_module_access():
        """Expose enabled module keys user can access as `module_access` and `user_obj` in all templates."""
        try:
            if not current_user.is_authenticated:
                return {"module_access": set(), "user_obj": None, "user_profile": None, "user_display": None}

            u = current_user.get_user()
            prof = RBUserProfile.query.get(u.user_id) if u else None

            display = None
            if prof:
                display = prof.display_name or prof.full_name or prof.rgDisplay
            if not display and u:
                display = u.email

            # Admin: show all enabled modules in nav.
            if getattr(u, "is_admin", False):
                keys = {m.module_key for m in RBModule.query.filter(RBModule.is_enabled == True).all()}
                return {"module_access": keys, "user_obj": u, "user_profile": prof, "user_display": display}

            keys = {
                r[0]
                for r in (
                    db.session.query(RBUserModule.module_key)
                    .join(RBModule, RBModule.module_key == RBUserModule.module_key)
                    .filter(RBUserModule.user_id == u.user_id)
                    .filter(RBUserModule.has_access == True)
                    .filter(RBModule.is_enabled == True)
                    .all()
                )
            }
            return {"module_access": keys, "user_obj": u, "user_profile": prof, "user_display": display}
        except Exception:
            # Never fail rendering due to DB issues.
            return {"module_access": set(), "user_obj": None, "user_profile": None, "user_display": None}


    # ─────────────────────────────
    # REGISTER MODULES HERE
    # ─────────────────────────────
    from modules.chat import register_chat_module
    register_chat_module(app)

    from modules.cv import register_cv_module
    register_cv_module(app)

    try:
        from modules.social import register_social_module
        register_social_module(app)
    except Exception:
        # Keep app booting even if optional module fails.
        pass

    try:
        from modules.services import register_services_module
        register_services_module(app)
    except Exception:
        pass

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
