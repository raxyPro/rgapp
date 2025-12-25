from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import uuid

from extensions import db
from models import RBUserProfile, RBAudit

user_bp = Blueprint("user", __name__, url_prefix="/app")

@user_bp.route("/welcome")
@login_required
def welcome():
    u = current_user.get_user()
    return render_template("welcome.html", user=u)

@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    u = current_user.get_user()
    prof = RBUserProfile.query.get(u.user_id)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        display_name = request.form.get("display_name", "").strip()

        prev = {"full_name": prof.full_name, "display_name": prof.display_name, "rgDisplay": prof.rgDisplay}

        prof.full_name = full_name or None
        prof.display_name = display_name or None
        prof.rgDisplay = display_name or full_name or u.email

        db.session.add(prof)
        db.session.add(RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_user_profile",
            row_id=u.user_id,
            action="edit",
            actor_id=u.user_id,
            source="self",
            prev_data=prev,
            new_data={"full_name": prof.full_name, "display_name": prof.display_name, "rgDisplay": prof.rgDisplay}
        ))
        db.session.commit()

        flash("Profile updated.", "success")
        return redirect(url_for("user.welcome"))

    return render_template("profile.html", profile=prof, email=u.email)
