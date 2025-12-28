from flask import Flask
from config import Config
from extensions import db, login_manager, socketio
from flask_login import current_user

from models import RBModule, RBUserModule, RBUserProfile

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode="threading", cors_allowed_origins="*")

    from routes_home import home_bp
    from routes_auth import auth_bp
    from routes_admin import admin_bp
    from routes_user import user_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

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
    socketio.run(app, debug=True)
