import os
from flask import Flask, redirect, request, url_for
from flask_login import current_user

from config import Config
from extensions import db, login_manager
from models import RBModule, RBUserModule, RBUserProfile


def create_app():
    app = Flask(__name__)

    # -------------------------------------------------
    # Load config (INI-based)
    # -------------------------------------------------
    app.config.from_object(Config)

    # -------------------------------------------------
    # SESSION / COOKIE CONFIG (CRITICAL)
    # -------------------------------------------------
    app.config.update(
        SESSION_COOKIE_PATH="/",
        REMEMBER_COOKIE_PATH="/",

        # Unique cookie names so multiple apps don't clash
        SESSION_COOKIE_NAME="bridge_session",
        REMEMBER_COOKIE_NAME="bridge_remember",

        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=True,  # HTTPS only
    )

    # Enable ONLY if you sometimes use www and sometimes not
    # app.config["SESSION_COOKIE_DOMAIN"] = ".raygrowcs.com"

    # -------------------------------------------------
    # Init extensions
    # -------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # -------------------------------------------------
    # Register blueprints
    # -------------------------------------------------
    import routes_home
    import routes_auth
    import routes_admin
    import routes_user

    app.register_blueprint(routes_home.home_bp)
    app.register_blueprint(routes_auth.auth_bp)
    app.register_blueprint(routes_admin.admin_bp)
    app.register_blueprint(routes_user.user_bp)

    # -------------------------------------------------
    # Short alias (always resolves correctly)
    # -------------------------------------------------
    @app.route("/welcome")
    def welcome_shortcut():
        return redirect(url_for("user.welcome"))

    # -------------------------------------------------
    # Disable caching of authenticated pages
    # -------------------------------------------------
    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # -------------------------------------------------
    # SUBPATH ENFORCEMENT (DISABLED FOR PASSENGER)
    # -------------------------------------------------
    # IMPORTANT:
    # PassengerBaseURI (/bridge) already handles mounting.
    # Enforcing subpath inside Flask causes redirect/session bugs.
    #
    # Therefore: only enforce subpath in DEV, never under Passenger.
    #
    subpath = (app.config.get("APP_SUBPATH") or "").strip("/")
    enforce_subpath = bool(app.config.get("APP_ENFORCE_SUBPATH", False))

    if os.environ.get("PASSENGER_BASE_URI"):
        enforce_subpath = False

    if subpath and enforce_subpath:
        prefix = f"/{subpath}"

        @app.before_request
        def _redirect_subpath():
            if request.path == prefix or request.path.startswith(prefix + "/"):
                return
            if request.path.startswith("/static/"):
                return
            return redirect(f"{prefix}{request.path}", code=302)

    # -------------------------------------------------
    # Template globals (module access)
    # -------------------------------------------------
    @app.context_processor
    def inject_module_access():
        try:
            if not current_user.is_authenticated:
                return {
                    "module_access": set(),
                    "user_obj": None,
                    "user_profile": None,
                    "user_display": None,
                }

            u = current_user.get_user()
            prof = RBUserProfile.query.get(u.user_id) if u else None

            display = None
            if prof:
                display = prof.display_name or prof.full_name or prof.rgDisplay
            if not display and u:
                display = u.email

            # Admin → all enabled modules
            if getattr(u, "is_admin", False):
                keys = {
                    m.module_key
                    for m in RBModule.query.filter(RBModule.is_enabled == True).all()
                }
                return {
                    "module_access": keys,
                    "user_obj": u,
                    "user_profile": prof,
                    "user_display": display,
                }

            # Normal user → granted modules
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

            return {
                "module_access": keys,
                "user_obj": u,
                "user_profile": prof,
                "user_display": display,
            }

        except Exception:
            # Never break rendering due to DB issues
            return {
                "module_access": set(),
                "user_obj": None,
                "user_profile": None,
                "user_display": None,
            }

    # -------------------------------------------------
    # Register feature modules
    # -------------------------------------------------
    from modules.chat import register_chat_module
    register_chat_module(app)

    from modules.cv import register_cv_module
    register_cv_module(app)

    try:
        from modules.social import register_social_module
        register_social_module(app)
    except Exception:
        pass

    try:
        from modules.services import register_services_module
        register_services_module(app)
    except Exception:
        pass

    return app


# Passenger entry
app = create_app()

# Local dev only
if __name__ == "__main__":
    app.run(debug=True)
