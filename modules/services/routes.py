from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from models import RBUser, RBUserProfile
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.cv.models import RBVCard, RBVCardItem

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

    vcards = RBVCard.query.all()
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
        items = RBVCardItem.query.filter(RBVCardItem.vcard_id.in_([v.vcard_id for v in vcards])).all()
        vcard_map = {v.vcard_id: v for v in vcards}
        for item in items:
            owner_id = vcard_map.get(item.vcard_id).user_id if vcard_map.get(item.vcard_id) else None
            if owner_id not in providers:
                continue
            if item.item_type == "skill":
                providers[owner_id]["skills"].append(item)
            elif item.item_type == "service":
                providers[owner_id]["services"].append(item)

    mine = providers.pop(me_id, None)
    others = list(providers.values())
    # Sort: first by handle/email for stability
    others.sort(key=lambda p: (p.get("handle") or p.get("email") or "").lower())

    return render_template("services/index.html", me=mine, others=others)
