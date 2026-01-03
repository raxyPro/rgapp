from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from typing import Optional
import uuid

from extensions import db
from models import RBUser, RBUserProfile, RBAudit, RBModule, RBUserModule
from modules.profiles.models import RBCVFileShare, RBCVProfile, RBCVShare, RBCVPair


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
    me_email = (u.email or "").strip().lower()
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

    # Notifications: CV shares to me
    notifications = []

    # CV file shares
    file_shares = (
        RBCVFileShare.query
        .filter((RBCVFileShare.target_user_id == u.user_id) | (RBCVFileShare.target_email == me_email))
        .order_by(RBCVFileShare.created_at.desc())
        .limit(50)
        .all()
    )
    file_ids = {s.cvfile_id for s in file_shares}
    file_map = {
        c.cvfile_id: c
        for c in RBCVProfile.query.filter(RBCVProfile.cvfile_id.in_(file_ids)).all()
    } if file_ids else {}

    # CV pair shares
    pair_shares = (
        RBCVShare.query
        .filter((RBCVShare.target_user_id == u.user_id) | (RBCVShare.target_email == me_email))
        .order_by(RBCVShare.created_at.desc())
        .limit(50)
        .all()
    )
    pair_ids = {s.cv_id for s in pair_shares}
    pair_map = {
        p.cv_id: p
        for p in RBCVPair.query.filter(RBCVPair.cv_id.in_(pair_ids)).all()
    } if pair_ids else {}

    owner_ids = {s.owner_user_id for s in file_shares} | {s.owner_user_id for s in pair_shares}
    owners = {usr.user_id: usr for usr in RBUser.query.filter(RBUser.user_id.in_(owner_ids)).all()} if owner_ids else {}
    owner_profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(owner_ids)).all()} if owner_ids else {}

    def _owner_label(owner_id):
        usr = owners.get(owner_id)
        prof = owner_profiles.get(owner_id)
        if prof and prof.handle:
            return prof.handle
        if usr and usr.email:
            return usr.email
        return f"User #{owner_id}"

    for s in file_shares:
        cv = file_map.get(s.cvfile_id)
        notifications.append({
            "ts": getattr(s, "created_at", None),
            "type": "CV File",
            "name": cv.cv_name if cv else f"CV #{s.cvfile_id}",
            "from": _owner_label(s.owner_user_id),
            "link": url_for("profileviewer.view", token=s.share_token),
        })

    for s in pair_shares:
        cv = pair_map.get(s.cv_id)
        name = (
            getattr(cv, "cv_name", None)
            or getattr(cv, "op_name", None)
            or getattr(cv, "v_name", None)
            or f"CV Pair #{s.cv_id}"
        )
        notifications.append({
            "ts": getattr(s, "created_at", None),
            "type": "CV Pair",
            "name": name,
            "from": _owner_label(s.owner_user_id),
            "link": url_for("profileviewer.view_pair", token=s.share_token),
        })

    notifications.sort(key=lambda n: n.get("ts") or 0, reverse=True)

    return render_template("welcome.html", user=u, modules=modules, notifications=notifications)

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
