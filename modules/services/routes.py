from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from models import RBUser, RBUserProfile
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.profiles.models import RBCVProfile

services_bp = Blueprint(
    "services",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/services",
)


@services_bp.get("/")
@login_required
@module_required("services")
def index():
    me_id = get_current_user_id()

    users = {u.user_id: u for u in RBUser.query.all()}
    profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(users.keys())).all()}

    vcards = RBCVProfile.query.filter_by(doc_type="vcard").all()
    providers = {}
    for v in vcards:
        # Only list vcards with a tagline to keep the catalogue meaningful.
        if not (v.tagline or "").strip():
            continue
        u = users.get(v.user_id)
        if not u:
            continue
        prof = profiles.get(v.user_id)
        providers[v.user_id] = {
            "user_id": v.user_id,
            "handle": getattr(prof, "handle", None),
            "email": u.email,
            "tagline": v.tagline,
            "name": v.name,
            "skills": [],
            "services": [],
        }

    if providers:
        for v in vcards:
            if v.user_id not in providers:
                continue
            providers[v.user_id]["skills"] = v.skills or []
            providers[v.user_id]["services"] = v.services or []

    mine = providers.pop(me_id, None)
    others = list(providers.values())
    # Sort: first by handle/email for stability
    others.sort(key=lambda p: (p.get("handle") or p.get("email") or "").lower())

    return render_template("services/index.html", me=mine, others=others)
