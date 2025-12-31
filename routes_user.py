from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from typing import Optional
import uuid

from extensions import db
from models import RBUserProfile, RBAudit, RBModule, RBUserModule


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

user_bp = Blueprint("user", __name__)

@user_bp.route("/welcome")
@login_required
def welcome():
    u = current_user.get_user()
    # Only show modules explicitly granted to the user AND globally enabled.
    modules = (
        RBModule.query
        .join(RBUserModule, RBUserModule.module_key == RBModule.module_key)
        .filter(RBUserModule.user_id == u.user_id)
        .filter(RBUserModule.has_access == True)
        .filter(RBModule.is_enabled == True)
        .order_by(RBModule.module_key.asc())
        .all()
    )
    return render_template("welcome.html", user=u, modules=modules)

@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    u = current_user.get_user()
    prof = RBUserProfile.query.get(u.user_id)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        handle = request.form.get("handle", "").strip()

        prev = {"full_name": prof.full_name, "display_name": prof.display_name, "rgDisplay": prof.rgDisplay}

        prof.full_name = full_name or None
        prof.display_name = display_name or None
        prof.rgDisplay = display_name or full_name or u.email
        if handle:
            prof.handle = _unique_handle(handle, user_id=u.user_id)

        db.session.add(prof)
        db.session.add(RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_user_profile",
            row_id=u.user_id,
            action="edit",
            actor_id=u.user_id,
            source="self",
            prev_data=prev,
            new_data={"full_name": prof.full_name, "display_name": prof.display_name, "rgDisplay": prof.rgDisplay, "handle": prof.handle}
        ))
        db.session.commit()

        flash("Profile updated.", "success")
        return redirect(url_for("user.welcome"))

    return render_template("profile.html", profile=prof, email=u.email)


# Backward compatibility for old /app/welcome path
@user_bp.route("/app/welcome")
def welcome_legacy():
    return redirect(url_for("user.welcome"))
