from tokens import generate_reset_token
from emailer import send_reset_email
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from passlib.hash import bcrypt
import uuid

from extensions import db
from models import RBUser, RBUserProfile, RBAudit, RBModule, RBUserModule
from tokens import generate_invite_token
from emailer import send_invite_email

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def _unique_handle(base: str, user_id: Optional[int] = None) -> str:
    handle = "".join(ch.lower() if ch.isalnum() or ch in ("_", ".") else "-" for ch in base).strip("-._")
    handle = handle or "user"
    candidate = handle
    suffix = 1
    while True:
        exists = RBUserProfile.query.filter(RBUserProfile.handle == candidate)
        if user_id:
            exists = exists.filter(RBUserProfile.user_id != user_id)
        if not exists.first():
            return candidate
        suffix += 1
        candidate = f"{handle}{suffix}"

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user.get_user()
        if not u.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapper

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    users = RBUser.query.order_by(RBUser.created_at.desc()).all()
    return render_template("admin.html", users=users)


@admin_bp.route("/modules/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def user_modules(user_id):
    admin_user = current_user.get_user()

    u = RBUser.query.get(user_id)
    if not u or u.status in ("deleted",):
        flash("User not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    modules = RBModule.query.order_by(RBModule.module_key.asc()).all()
    existing = {
        um.module_key: um
        for um in RBUserModule.query.filter_by(user_id=u.user_id).all()
    }

    if request.method == "POST":
        # Checkbox values: module_key present => granted, else revoked.
        requested_keys = set(request.form.getlist("modules"))

        changed = False
        for m in modules:
            has_row = m.module_key in existing

            if m.module_key in requested_keys and not has_row:
                db.session.add(
                    RBUserModule(
                        user_id=u.user_id,
                        module_key=m.module_key,
                        has_access=True,
                        granted_by=admin_user.user_id,
                    )
                )
                db.session.add(
                    RBAudit(
                        event_id=str(uuid.uuid4()),
                        tblname="rb_user_module",
                        row_id=u.user_id,
                        action="edit",
                        actor_id=admin_user.user_id,
                        source="admin",
                        prev_data=None,
                        new_data={"module_key": m.module_key, "has_access": True},
                    )
                )
                changed = True

            if m.module_key not in requested_keys and has_row:
                db.session.delete(existing[m.module_key])
                db.session.add(
                    RBAudit(
                        event_id=str(uuid.uuid4()),
                        tblname="rb_user_module",
                        row_id=u.user_id,
                        action="edit",
                        actor_id=admin_user.user_id,
                        source="admin",
                        prev_data={"module_key": m.module_key, "has_access": True},
                        new_data={"module_key": m.module_key, "has_access": False},
                    )
                )
                changed = True

        if changed:
            db.session.commit()
            flash("Modules updated.", "success")
        else:
            flash("No changes.", "info")

        return redirect(url_for("admin.user_modules", user_id=u.user_id))

    assigned_keys = set(existing.keys())
    return render_template(
        "admin_modules.html",
        user=u,
        modules=modules,
        assigned_keys=assigned_keys,
    )

@admin_bp.route("/invite", methods=["GET", "POST"])
@login_required
@admin_required
def invite():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        handle_base = request.form.get("handle", "").strip() or display_name or full_name or email

        if not email or not full_name or not display_name:
            flash("Email, full name, and display name are required.", "danger")
            return render_template("invite.html", email=email, full_name=full_name, display_name=display_name)

        existing = RBUser.query.filter_by(email=email).first()
        if existing and existing.status != "deleted":
            flash("User already exists.", "warning")
            return render_template("invite.html", email=email, full_name=full_name, display_name=display_name)

        # Create invited user
        admin_user = current_user.get_user()

        u = RBUser(
            email=email,
            # Some databases/tables enforce NOT NULL; keep empty string until user sets password
            password_hash="",
            status="invited",
            is_admin=False,
            invited_at=datetime.utcnow(),
            invited_by=admin_user.user_id
        )
        db.session.add(u)
        db.session.flush()  # get user_id without commit

        prof = RBUserProfile(
            user_id=u.user_id,
            rgDisplay=(display_name or full_name or email),
            full_name=(full_name or None),
            display_name=(display_name or None),
            handle=_unique_handle(handle_base, user_id=u.user_id),
            rgData={}
        )
        db.session.add(prof)

        # Default grant: social module if enabled
        social_mod = RBModule.query.filter_by(module_key="social", is_enabled=True).first()
        if social_mod:
            db.session.add(RBUserModule(user_id=u.user_id, module_key="social", has_access=True, granted_by=admin_user.user_id))

        services_mod = RBModule.query.filter_by(module_key="services", is_enabled=True).first()
        if services_mod:
            db.session.add(RBUserModule(user_id=u.user_id, module_key="services", has_access=True, granted_by=admin_user.user_id))

        cv_mod = RBModule.query.filter_by(module_key="cv", is_enabled=True).first()
        if cv_mod:
            db.session.add(RBUserModule(user_id=u.user_id, module_key="cv", has_access=True, granted_by=admin_user.user_id))

        event_id = str(uuid.uuid4())
        db.session.add(RBAudit(
            event_id=event_id,
            tblname="rb_user",
            row_id=u.user_id,
            action="invite",
            actor_id=admin_user.user_id,
            source="admin",
            prev_data=None,
            new_data={"email": email, "status": "invited"}
        ))

        db.session.commit()

        token = generate_invite_token(email)
        base_url = current_app.config.get("REGISTER_BASE_URL") or current_app.config.get("APP_BASE_URL")
        invite_url = f"{base_url.rstrip('/')}/register/{token}"
        send_invite_email(email, invite_url)

        flash("Invitation sent.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("invite.html")

@admin_bp.route("/user/<int:user_id>/send_invite", methods=["POST"])
@login_required
@admin_required
def send_invite(user_id: int):
    admin_user = current_user.get_user()
    u = RBUser.query.get_or_404(user_id)
    if u.status == "active":
        flash("User is already active; invite disabled.", "info")
        return redirect(url_for("admin.dashboard"))

    token = generate_invite_token(u.email)
    base_url = current_app.config.get("REGISTER_BASE_URL") or current_app.config.get("APP_BASE_URL")
    invite_url = f"{base_url.rstrip('/')}/register/{token}"
    send_invite_email(u.email, invite_url)

    db.session.add(RBAudit(
        event_id=str(uuid.uuid4()),
        tblname="rb_user",
        row_id=u.user_id,
        action="invite",
        actor_id=admin_user.user_id,
        source="admin",
        prev_data=None,
        new_data={"email": u.email, "status": u.status, "invite_sent_at": datetime.utcnow().isoformat()}
    ))
    db.session.commit()
    flash("Invitation sent.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/user/<int:user_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_user(user_id: int):
    admin_user = current_user.get_user()
    u = RBUser.query.get_or_404(user_id)
    if u.status == "deleted":
        flash("User already deleted.", "warning")
        return redirect(url_for("admin.dashboard"))

    prev_status = u.status
    u.status = "blocked"
    db.session.add(u)
    db.session.add(RBAudit(
        event_id=str(uuid.uuid4()),
        tblname="rb_user",
        row_id=u.user_id,
        action="edit",
        actor_id=admin_user.user_id,
        source="admin",
        prev_data={"status": prev_status},
        new_data={"status": "blocked"}
    ))
    db.session.commit()
    flash("User set to inactive.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int):
    u = RBUser.query.get_or_404(user_id)
    prof = RBUserProfile.query.get(u.user_id)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        is_admin = bool(request.form.get("is_admin"))
        handle = (request.form.get("handle") or "").strip()

        u.is_admin = is_admin
        db.session.add(u)

        if prof:
            prof.full_name = full_name or None
            prof.display_name = display_name or None
            prof.rgDisplay = display_name or full_name or u.email
            if handle:
                prof.handle = _unique_handle(handle, user_id=u.user_id)
            db.session.add(prof)

        db.session.add(RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_user",
            row_id=u.user_id,
            action="edit",
            actor_id=current_user.get_user().user_id,
            source="admin",
            prev_data=None,
            new_data={"full_name": full_name, "display_name": display_name, "is_admin": is_admin}
        ))
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin_edit_user.html", user=u, profile=prof)

@admin_bp.route("/reset/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def admin_reset_password(user_id):
    admin_user = current_user.get_user()

    u = RBUser.query.get(user_id)
    if not u or u.status in ("deleted",):
        flash("User not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    if u.status != "active":
        flash("Password reset can be sent only to ACTIVE users.", "warning")
        return redirect(url_for("admin.dashboard"))

    token = generate_reset_token(u.email)
    reset_url = f"{current_app.config['APP_BASE_URL'].rstrip('/')}/reset/{token}"

    # Send reset email
    send_reset_email(u.email, reset_url)

    # Audit
    db.session.add(RBAudit(
        event_id=str(uuid.uuid4()),
        tblname="rb_user",
        row_id=u.user_id,
        audit_date=datetime.utcnow(),
        action="edit",
        actor_id=admin_user.user_id,
        source="admin",
        prev_data=None,
        new_data={"admin_password_reset_sent": True, "to": u.email}
    ))
    db.session.commit()

    flash(f"Reset link sent to {u.email}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/viewlog", methods=["GET"])
@login_required
@admin_required
def view_log():
    log_path = Path(current_app.root_path) / "stderr.log"

    if not log_path.exists():
        flash("stderr.log not found.", "warning")
        return redirect(url_for("admin.dashboard"))

    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as exc:
        flash(f"Unable to read stderr.log: {exc}", "danger")
        return redirect(url_for("admin.dashboard"))

    # Limit to last 400 lines to keep page responsive.
    tail_lines = "".join(lines[-400:])
    return render_template("admin_log.html", log_text=tail_lines, log_path=str(log_path))
