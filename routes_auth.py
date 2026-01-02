from tokens import generate_reset_token, verify_reset_token
from emailer import send_reset_email
from security import hash_password, verify_password
from flask import current_app

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from pathlib import Path
from flask_login import login_user, logout_user, current_user
from security import verify_password, hash_password


from extensions import db, login_manager
from models import RBUser, RBUserProfile, RBAudit, RBModule, RBUserModule
from tokens import verify_invite_token
import uuid

auth_bp = Blueprint("auth", __name__)

class UserLoginAdapter:
    """Flask-Login expects specific properties/methods."""
    def __init__(self, user: RBUser):
        self._u = user

    @property
    def id(self):
        return str(self._u.user_id)

    def get_id(self):
        return str(self._u.user_id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self._u.status in ("active",)

    @property
    def is_anonymous(self):
        return False

    def get_user(self):
        return self._u

@login_manager.user_loader
def load_user(user_id: str):
    u = RBUser.query.get(int(user_id))
    return UserLoginAdapter(u) if u else None

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        u = current_user.get_user()
        return redirect(url_for("admin.dashboard" if u.is_admin else "user.welcome"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        u = RBUser.query.filter_by(email=email).first()
        if not u or not u.password_hash:
            flash("Invalid credentials.", "danger")
            return render_template("login.html")

        if u.status != "active":
            flash("Account not active. Please contact admin.", "warning")
            return render_template("login.html")

        if not verify_password(password, u.password_hash):

            flash("Invalid credentials.", "danger")
            return render_template("login.html")

        u.last_login_at = datetime.utcnow()
        db.session.add(u)

        db.session.add(RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_user",
            row_id=u.user_id,
            action="login",
            actor_id=u.user_id,
            source="self",
            prev_data=None,
            new_data={"email": u.email, "at": u.last_login_at.isoformat()}
        ))

        # Default: grant social module if enabled
        _ensure_module_access(u.user_id, "social")
        _ensure_module_access(u.user_id, "services")
        _ensure_module_access(u.user_id, "cv")
        db.session.commit()

        login_user(UserLoginAdapter(u))
        return redirect(url_for("admin.dashboard" if u.is_admin else "user.welcome"))

    return render_template("login.html")


def _dev_login_allowed():
    if not current_app.config.get("DEV_LOGIN_ENABLED"):
        return False
    # Only allow on explicit dev host
    host = request.host.split("//")[-1]
    if host != "127.0.0.1:5000":
        return False
    tpl_path = Path(current_app.root_path) / "templates" / "dev_login.html"
    return tpl_path.exists()


@auth_bp.route("/dev-login", methods=["GET", "POST"])
def dev_login():
    if not _dev_login_allowed():
        abort(404)

    if request.method == "POST":
        user_id_raw = request.form.get("user_id")
        if not user_id_raw or not str(user_id_raw).isdigit():
            flash("Choose a user to log in as.", "warning")
            return redirect(url_for("auth.dev_login"))
        u = RBUser.query.get(int(user_id_raw))
        if not u:
            flash("User not found.", "danger")
            return redirect(url_for("auth.dev_login"))
        login_user(UserLoginAdapter(u))
        flash(f"Logged in as {u.email}", "success")
        return redirect(url_for("admin.dashboard" if u.is_admin else "user.welcome"))

    users = (
        db.session.query(RBUser, RBUserProfile)
        .outerjoin(RBUserProfile, RBUserProfile.user_id == RBUser.user_id)
        .order_by(RBUser.email.asc())
        .all()
    )
    items = []
    for u, prof in users:
        items.append({
            "id": u.user_id,
            "email": u.email,
            "name": getattr(prof, "display_name", None) or getattr(prof, "full_name", None),
            "handle": getattr(prof, "handle", None) or getattr(u, "handle", None),
            "status": u.status,
            "is_admin": getattr(u, "is_admin", False),
        })
    return render_template("dev_login.html", users=items)

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@auth_bp.route("/register/<token>", methods=["GET", "POST"])
def register(token):
    try:
        payload = verify_invite_token(token)
        email = payload["email"].strip().lower()
    except Exception:
        flash("Invalid or expired invitation link.", "danger")
        return redirect(url_for("auth.login"))

    u = RBUser.query.filter_by(email=email).first()
    if not u or u.status != "invited":
        flash("Invitation is not valid or already used.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html", email=email)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", email=email)

        u.password_hash = hash_password(password)

        u.status = "active"         # Invite acceptance activates user (admin already approved by inviting)
        u.registered_at = datetime.utcnow()
        db.session.add(u)

        # Ensure profile exists
        prof = RBUserProfile.query.get(u.user_id)
        if not prof:
            prof = RBUserProfile(user_id=u.user_id, rgDisplay=email, full_name=None, display_name=None, rgData={})
            db.session.add(prof)

        db.session.add(RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_user",
            row_id=u.user_id,
            action="register",
            actor_id=u.user_id,
            source="self",
            prev_data={"status": "invited"},
            new_data={"status": "active", "registered_at": u.registered_at.isoformat()}
        ))

        db.session.commit()
        flash("Registration complete. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", email=email)

@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        # Always show same message to avoid leaking which emails exist
        flash("If the email exists, a reset link has been sent.", "info")

        if email:
            u = RBUser.query.filter_by(email=email).first()
            # Only allow reset for real active users
            if u and u.status == "active":
                token = generate_reset_token(email)
                reset_url = f"{current_app.config['APP_BASE_URL'].rstrip('/')}/reset/{token}"
                send_reset_email(email, reset_url)

                db.session.add(RBAudit(
                    event_id=str(uuid.uuid4()),
                    tblname="rb_user",
                    row_id=u.user_id,
                    action="edit",
                    actor_id=u.user_id,
                    source="self",
                    prev_data=None,
                    new_data={"password_reset_requested_at": datetime.utcnow().isoformat()}
                ))
                db.session.commit()

        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        payload = verify_reset_token(token)   # 30 mins default
        email = payload["email"].strip().lower()
    except Exception:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.login"))

    u = RBUser.query.filter_by(email=email).first()
    if not u or u.status != "active":
        flash("Reset link not valid for this account.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", email=email)

        try:
            u.password_hash = hash_password(password)
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("reset_password.html", email=email)

        db.session.add(u)
        db.session.add(RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_user",
            row_id=u.user_id,
            action="edit",
            actor_id=u.user_id,
            source="self",
            prev_data=None,
            new_data={"password_reset_at": datetime.utcnow().isoformat()}
        ))
        db.session.commit()

        flash("Password updated. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", email=email)
def _ensure_module_access(user_id: int, module_key: str):
    mod = RBModule.query.filter_by(module_key=module_key, is_enabled=True).first()
    if not mod:
        return
    exists = RBUserModule.query.filter_by(user_id=user_id, module_key=module_key).first()
    if not exists:
        db.session.add(RBUserModule(user_id=user_id, module_key=module_key, has_access=True))
