from __future__ import annotations

import secrets
from datetime import datetime

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import login_required, current_user

from extensions import db
from models import RBUser
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.cv.models import RBCVPair, RBCVShare
from modules.cv.util import generate_onepage_html


cv_bp = Blueprint(
    "cv",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/cv",
)

cvviewer_bp = Blueprint(
    "cvviewer",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/cvviewer",
)


def _token() -> str:
    return secrets.token_urlsafe(32)[:64]


def _get_pair_or_404(cv_id: int) -> RBCVPair:
    p = RBCVPair.query.get_or_404(cv_id)
    return p


def _ensure_owner(pair: RBCVPair, user_id: int):
    if pair.user_id != user_id:
        abort(403)


@cv_bp.get("/")
@login_required
@module_required("cv")
def home():
    me_id = get_current_user_id()
    active = (
        RBCVPair.query
        .filter_by(user_id=me_id, is_archived=False)
        .order_by(RBCVPair.updated_at.desc())
        .all()
    )
    archived = (
        RBCVPair.query
        .filter_by(user_id=me_id, is_archived=True)
        .order_by(RBCVPair.updated_at.desc())
        .all()
    )
    return render_template("cv/home.html", active=active, archived=archived)


@cv_bp.post("/new")
@login_required
@module_required("cv")
def new_pair():
    me_id = get_current_user_id()
    p = RBCVPair(user_id=me_id)
    p.onepage_html = generate_onepage_html(p)
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("cv.edit_vcard", cv_id=p.cv_id))


@cv_bp.get("/<int:cv_id>/edit")
@login_required
@module_required("cv")
def edit_vcard(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)
    return render_template("cv/edit_vcard.html", p=p)


@cv_bp.post("/<int:cv_id>/edit")
@login_required
@module_required("cv")
def save_vcard(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)

    # Save vCard fields
    p.v_name = (request.form.get("v_name") or "").strip()
    p.v_company = (request.form.get("v_company") or "").strip()
    p.v_email = (request.form.get("v_email") or "").strip()
    p.v_phone = (request.form.get("v_phone") or "").strip()
    p.v_primary_skill = (request.form.get("v_primary_skill") or "").strip()
    p.v_skill_description = (request.form.get("v_skill_description") or "").strip()
    p.v_organizations = (request.form.get("v_organizations") or "").strip()
    p.v_achievements = (request.form.get("v_achievements") or "").strip()

    # Generate one-page CV
    p.onepage_html = generate_onepage_html(p)
    p.updated_at = datetime.utcnow()

    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.post("/<int:cv_id>/cancel")
@login_required
@module_required("cv")
def cancel_edit(cv_id: int):
    # No state change; just go back
    return redirect(url_for("cv.home"))


@cv_bp.get("/<int:cv_id>/view")
@login_required
@module_required("cv")
def view_onepage(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)
    return render_template("cv/view_onepage.html", p=p)


@cv_bp.post("/<int:cv_id>/archive")
@login_required
@module_required("cv")
def archive(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)
    p.is_archived = True
    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.post("/<int:cv_id>/unarchive")
@login_required
@module_required("cv")
def unarchive(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)
    p.is_archived = False
    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.get("/<int:cv_id>/share")
@login_required
@module_required("cv")
def share(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)

    # Existing shares
    shares = (
        RBCVShare.query
        .filter_by(cv_id=cv_id, owner_user_id=me_id)
        .order_by(RBCVShare.created_at.desc())
        .all()
    )

    # User list for sharing
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()

    public_share = next((s for s in shares if s.is_public), None)
    public_link = url_for("cvviewer.view", token=public_share.share_token, _external=True) if public_share else None

    return render_template(
        "cv/share.html",
        p=p,
        shares=shares,
        users=users,
        public_link=public_link,
    )


@cv_bp.post("/<int:cv_id>/share/public")
@login_required
@module_required("cv")
def share_public(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)

    # Reuse if exists
    s = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, is_public=True).first()
    if not s:
        s = RBCVShare(
            cv_id=cv_id,
            owner_user_id=me_id,
            target_user_id=None,
            target_email=None,
            share_token=_token(),
            is_public=True,
        )
        db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share", cv_id=cv_id))


@cv_bp.post("/<int:cv_id>/share/user")
@login_required
@module_required("cv")
def share_user(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")

    target_user_id = int(target_user_id)

    exists = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("cv.share", cv_id=cv_id))

    s = RBCVShare(
        cv_id=cv_id,
        owner_user_id=me_id,
        target_user_id=target_user_id,
        target_email=None,
        share_token=_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share", cv_id=cv_id))


@cv_bp.post("/<int:cv_id>/share/email")
@login_required
@module_required("cv")
def share_email(cv_id: int):
    me_id = get_current_user_id()
    p = _get_pair_or_404(cv_id)
    _ensure_owner(p, me_id)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("cv.share", cv_id=cv_id))

    s = RBCVShare(
        cv_id=cv_id,
        owner_user_id=me_id,
        target_user_id=None,
        target_email=email,
        share_token=_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share", cv_id=cv_id))


@cv_bp.get("/shared")
@login_required
@module_required("cv")
def shared_with_me():
    me_id = get_current_user_id()
    me = current_user.get_user() if hasattr(current_user, "get_user") else None
    me_email = (getattr(me, "email", "") or "").lower()

    q = RBCVShare.query
    q = q.filter((RBCVShare.target_user_id == me_id) | (RBCVShare.target_email == me_email))
    shares = q.order_by(RBCVShare.created_at.desc()).all()

    active = [s for s in shares if not s.is_archived]
    archived = [s for s in shares if s.is_archived]

    # Load pairs and owners
    cv_ids = list({s.cv_id for s in shares})
    pairs = {p.cv_id: p for p in RBCVPair.query.filter(RBCVPair.cv_id.in_(cv_ids)).all()} if cv_ids else {}

    owner_ids = list({s.owner_user_id for s in shares})
    owners = {u.user_id: u for u in RBUser.query.filter(RBUser.user_id.in_(owner_ids)).all()} if owner_ids else {}

    return render_template(
        "cv/shared_with_me.html",
        active=active,
        archived=archived,
        pairs=pairs,
        owners=owners,
    )


@cv_bp.post("/shared/<int:share_id>/archive")
@login_required
@module_required("cv")
def archive_share(share_id: int):
    me_id = get_current_user_id()
    s = RBCVShare.query.get_or_404(share_id)
    if not (s.target_user_id == me_id or s.target_email):
        abort(403)
    s.is_archived = True
    db.session.commit()
    return redirect(url_for("cv.shared_with_me"))


@cv_bp.post("/shared/<int:share_id>/unarchive")
@login_required
@module_required("cv")
def unarchive_share(share_id: int):
    me_id = get_current_user_id()
    s = RBCVShare.query.get_or_404(share_id)
    if not (s.target_user_id == me_id or s.target_email):
        abort(403)
    s.is_archived = False
    db.session.commit()
    return redirect(url_for("cv.shared_with_me"))


@cv_bp.get("/shared/<int:share_id>/view")
@login_required
@module_required("cv")
def view_shared(share_id: int):
    me_id = get_current_user_id()
    me = current_user.get_user() if hasattr(current_user, "get_user") else None
    me_email = (getattr(me, "email", "") or "").lower()

    s = RBCVShare.query.get_or_404(share_id)
    if not (s.target_user_id == me_id or (s.target_email and s.target_email.lower() == me_email)):
        abort(403)

    p = _get_pair_or_404(s.cv_id)
    owner = RBUser.query.get(p.user_id)
    return render_template("cv/view_shared.html", p=p, owner=owner, share=s)


@cv_bp.get("/shared/<int:share_id>/message")
@login_required
@module_required("cv")
def message_owner(share_id: int):
    me_id = get_current_user_id()
    me = current_user.get_user() if hasattr(current_user, "get_user") else None
    me_email = (getattr(me, "email", "") or "").lower()

    s = RBCVShare.query.get_or_404(share_id)
    if not (s.target_user_id == me_id or (s.target_email and s.target_email.lower() == me_email)):
        abort(403)
    return redirect(url_for("chat.start_dm", user_id=s.owner_user_id))


@cvviewer_bp.get("/<token>")
def view(token: str):
    s = RBCVShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        abort(403)

    p = _get_pair_or_404(s.cv_id)
    owner = RBUser.query.get(p.user_id)
    return render_template("cv/view_public.html", p=p, owner=owner)
