import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import time
from flask import Flask, redirect, request, url_for, g
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
    # HTTP traffic logging (requests + responses)
    # -------------------------------------------------
    http_logger = None
    if app.config.get("HTTP_LOG_ENABLED"):
        # Avoid noisy stderr when rotation fails (e.g., on Windows file locks).
        logging.raiseExceptions = False
        http_logger = logging.getLogger("http_traffic")
        http_logger.setLevel(logging.INFO)
        http_logger.propagate = False
        raw_dir = app.config.get("HTTP_LOG_DIR") or ""
        raw_path = app.config.get("HTTP_LOG_PATH") or "http.log"
        basename = app.config.get("HTTP_LOG_BASENAME") or Path(raw_path).name
        if raw_dir:
            log_path = Path(raw_dir)
            if not log_path.is_absolute():
                log_path = Path(app.root_path) / log_path
            log_path.mkdir(parents=True, exist_ok=True)
            log_path = log_path / basename
        else:
            log_path = Path(raw_path)
            if not log_path.is_absolute():
                log_path = Path(app.root_path) / raw_path
        try:
            has_handler = any(getattr(h, "_is_http_log_handler", False) for h in http_logger.handlers)
            if not has_handler:
                fh = TimedRotatingFileHandler(
                    log_path,
                    when="midnight",
                    interval=1,
                    backupCount=30,
                    encoding="utf-8",
                    utc=True,
                )
                fh.setLevel(logging.INFO)
                fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
                fh._is_http_log_handler = True
                http_logger.addHandler(fh)
        except Exception:
            http_logger = None

    def _safe_http_log(msg: str, *args):
        if not http_logger:
            return
        try:
            http_logger.info(msg, *args)
        except Exception:
            # Never block requests because of logging failures
            pass

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

    @app.before_request
    def _log_request():
        if not http_logger:
            return
        user_id = None
        if current_user and current_user.is_authenticated:
            u = current_user.get_user() if hasattr(current_user, "get_user") else None
            user_id = getattr(u, "user_id", None)
        g._http_log_ctx = {
            "started": time.time(),
            "user_id": user_id,
            "remote": request.headers.get("X-Forwarded-For", request.remote_addr),
            "ua": request.headers.get("User-Agent", "-"),
            "path": request.path,
            "qs": request.query_string.decode(errors="ignore") if request.query_string else "",
            "method": request.method,
        }
        _safe_http_log(
            "REQ method=%s path=%s qs=%s user=%s remote=%s ua=%s",
            g._http_log_ctx["method"],
            g._http_log_ctx["path"],
            g._http_log_ctx["qs"],
            user_id or "-",
            g._http_log_ctx["remote"] or "-",
            g._http_log_ctx["ua"],
        )

    @app.after_request
    def _log_response(response):
        if http_logger:
            ctx = getattr(g, "_http_log_ctx", {})
            started = ctx.get("started")
            duration_ms = int((time.time() - started) * 1000) if started else None
            content_length = response.calculate_content_length()
            _safe_http_log(
                "RES status=%s path=%s bytes=%s duration_ms=%s user=%s remote=%s",
                response.status_code,
                ctx.get("path") or request.path,
                content_length if content_length is not None else "-",
                duration_ms if duration_ms is not None else "-",
                ctx.get("user_id") or "-",
                ctx.get("remote") or request.headers.get("X-Forwarded-For", request.remote_addr),
            )
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
            def _with_aliases(keys):
                if "cv" in keys:
                    keys = set(keys)
                    keys.add("profiles")
                return keys

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
                    "module_access": _with_aliases(keys),
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
                "module_access": _with_aliases(keys),
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

    from modules.profiles import register_profiles_module
    register_profiles_module(app)

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

    # Legacy route shims (old CV module paths)
    @app.route("/cvviewer/<path:rest>")
    def legacy_cvviewer(rest):
        return redirect(f"/profileviewer/{rest}", code=302)

    @app.route("/cv/<path:rest>")
    @app.route("/cv", defaults={"rest": ""})
    def legacy_cv(rest):
        suffix = f"/{rest}" if rest else ""
        return redirect(f"/profiles{suffix}", code=302)

    return app


# Passenger entry
app = create_app()

# Local dev only
if __name__ == "__main__":
    app.run(debug=True)
