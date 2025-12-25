from tokens import generate_reset_token
from emailer import send_reset_email
import uuid
from datetime import datetime

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from passlib.hash import bcrypt
import uuid

from extensions import db
from models import RBUser, RBUserProfile, RBAudit
from tokens import generate_invite_token
from emailer import send_invite_email

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

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

@admin_bp.route("/invite", methods=["GET", "POST"])
@login_required
@admin_required
def invite():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        display_name = request.form.get("display_name", "").strip()

        if not email:
            flash("Email is required.", "danger")
            return render_template("invite.html")

        existing = RBUser.query.filter_by(email=email).first()
        if existing and existing.status != "deleted":
            flash("User already exists.", "warning")
            return render_template("invite.html")

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
            rgData={}
        )
        db.session.add(prof)

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
        invite_url = f"{current_app.config['APP_BASE_URL'].rstrip('/')}/register/{token}"
        send_invite_email(email, invite_url)

        flash("Invitation sent.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("invite.html")

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
