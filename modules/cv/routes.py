from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, redirect, render_template, request, url_for, send_file, current_app
from flask_login import login_required, current_user

from extensions import db
from models import RBUser
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.cv.models import RBVCard, RBVCardItem, RBCVFile, RBVCardShare, RBCVFileShare
from modules.cv.util import make_token, sanitize_filename, allowed_pdf


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

vcardviewer_bp = Blueprint(
    "vcardviewer",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/vcardviewer",
)


def _current_user_email_lower() -> str:
    me = current_user.get_user() if hasattr(current_user, "get_user") else None
    return (getattr(me, "email", "") or "").strip().lower()


def _get_or_create_vcard(user_id: int) -> RBVCard:
    v = RBVCard.query.filter_by(user_id=user_id).first()
    if not v:
        v = RBVCard(user_id=user_id)
        db.session.add(v)
        db.session.commit()
    return v


def _vcard_items(vcard_id: int):
    items = (
        RBVCardItem.query
        .filter_by(vcard_id=vcard_id)
        .order_by(RBVCardItem.item_type.asc(), RBVCardItem.sort_order.asc(), RBVCardItem.item_id.asc())
        .all()
    )
    skills = [i for i in items if i.item_type == "skill"]
    services = [i for i in items if i.item_type == "service"]
    return skills, services


def _uploads_root() -> Path:
    # Store uploads next to project root by default: <project>/uploads
    # You can override with app config CV_UPLOAD_DIR
    cfg = current_app.config.get("CV_UPLOAD_DIR") if current_app else None
    if cfg:
        return Path(cfg)
    return Path(current_app.root_path).parent / "uploads"


def _cv_user_dir(user_id: int) -> Path:
    d = _uploads_root() / "cv" / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _can_access_share_target(target_user_id: int | None, target_email: str | None, me_id: int, me_email: str) -> bool:
    if target_user_id is not None and target_user_id == me_id:
        return True
    if target_email and target_email.strip().lower() == me_email:
        return True
    return False


@cv_bp.get("/")
@login_required
@module_required("cv")
def home():
    me_id = get_current_user_id()
    me_email = _current_user_email_lower()

    vcard = _get_or_create_vcard(me_id)
    skills, services = _vcard_items(vcard.vcard_id)

    cv_files = (
        RBCVFile.query
        .filter_by(owner_user_id=me_id, is_archived=False)
        .order_by(RBCVFile.updated_at.desc())
        .all()
    )

    # Shares received
    vcard_shares = (
        RBVCardShare.query
        .filter((RBVCardShare.target_user_id == me_id) | (RBVCardShare.target_email == me_email))
        .order_by(RBVCardShare.created_at.desc())
        .all()
    )
    cvfile_shares = (
        RBCVFileShare.query
        .filter((RBCVFileShare.target_user_id == me_id) | (RBCVFileShare.target_email == me_email))
        .order_by(RBCVFileShare.created_at.desc())
        .all()
    )

    # Owners for display
    owner_ids = list({s.owner_user_id for s in (vcard_shares + cvfile_shares)})
    owners = {u.user_id: u for u in RBUser.query.filter(RBUser.user_id.in_(owner_ids)).all()} if owner_ids else {}

    # Assets maps
    shared_vcard_ids = list({s.vcard_id for s in vcard_shares})
    shared_vcards = {v.vcard_id: v for v in RBVCard.query.filter(RBVCard.vcard_id.in_(shared_vcard_ids)).all()} if shared_vcard_ids else {}

    shared_cvfile_ids = list({s.cvfile_id for s in cvfile_shares})
    shared_cvfiles = {c.cvfile_id: c for c in RBCVFile.query.filter(RBCVFile.cvfile_id.in_(shared_cvfile_ids)).all()} if shared_cvfile_ids else {}

    return render_template(
        "cv/home.html",
        vcard=vcard,
        skills=skills,
        services=services,
        cv_files=cv_files,
        vcard_shares=vcard_shares,
        cvfile_shares=cvfile_shares,
        owners=owners,
        shared_vcards=shared_vcards,
        shared_cvfiles=shared_cvfiles,
    )


# ─────────────────────────────
# vCard edit
# ─────────────────────────────
@cv_bp.get("/vcard/edit")
@login_required
@module_required("cv")
def edit_vcard():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)
    skills, services = _vcard_items(vcard.vcard_id)
    return render_template("cv/edit_vcard.html", vcard=vcard, skills=skills, services=services)


@cv_bp.post("/vcard/edit")
@login_required
@module_required("cv")
def save_vcard():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    vcard.name = (request.form.get("name") or "").strip()
    vcard.email = (request.form.get("email") or "").strip()
    vcard.linkedin_url = (request.form.get("linkedin_url") or "").strip()
    vcard.phone = (request.form.get("phone") or "").strip()
    vcard.tagline = (request.form.get("tagline") or "").strip()
    vcard.touch()

    # Replace items (simple + reliable)
    RBVCardItem.query.filter_by(vcard_id=vcard.vcard_id).delete()

    def _ingest(kind: str, titles, descs, exps):
        for idx, t in enumerate(titles):
            title = (t or "").strip()
            if not title:
                continue
            desc = (descs[idx] if idx < len(descs) else "") or ""
            exp = (exps[idx] if idx < len(exps) else "") or ""
            item = RBVCardItem(
                vcard_id=vcard.vcard_id,
                item_type=kind,
                title=title.strip(),
                description=desc.strip(),
                experience=exp.strip(),
                sort_order=idx,
            )
            db.session.add(item)

    _ingest(
        "skill",
        request.form.getlist("skill_title[]"),
        request.form.getlist("skill_desc[]"),
        request.form.getlist("skill_exp[]"),
    )
    _ingest(
        "service",
        request.form.getlist("service_title[]"),
        request.form.getlist("service_desc[]"),
        request.form.getlist("service_exp[]"),
    )

    db.session.commit()
    return redirect(url_for("cv.home"))


# ─────────────────────────────
# vCard sharing
# ─────────────────────────────
@cv_bp.get("/vcard/share")
@login_required
@module_required("cv")
def share_vcard():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    shares = (
        RBVCardShare.query
        .filter_by(vcard_id=vcard.vcard_id, owner_user_id=me_id)
        .order_by(RBVCardShare.created_at.desc())
        .all()
    )
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()

    public_share = next((s for s in shares if s.is_public), None)
    public_link = url_for("vcardviewer.view", token=public_share.share_token, _external=True) if public_share else None

    return render_template("cv/share_vcard.html", vcard=vcard, shares=shares, users=users, public_link=public_link)


@cv_bp.post("/vcard/share/public")
@login_required
@module_required("cv")
def share_vcard_public():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    s = RBVCardShare.query.filter_by(vcard_id=vcard.vcard_id, owner_user_id=me_id, is_public=True).first()
    if not s:
        s = RBVCardShare(
            vcard_id=vcard.vcard_id,
            owner_user_id=me_id,
            target_user_id=None,
            target_email=None,
            share_token=make_token(),
            is_public=True,
        )
        db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_vcard"))


@cv_bp.post("/vcard/share/user")
@login_required
@module_required("cv")
def share_vcard_user():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")
    target_user_id = int(target_user_id)

    exists = RBVCardShare.query.filter_by(vcard_id=vcard.vcard_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("cv.share_vcard"))

    s = RBVCardShare(
        vcard_id=vcard.vcard_id,
        owner_user_id=me_id,
        target_user_id=target_user_id,
        target_email=None,
        share_token=make_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_vcard"))


@cv_bp.post("/vcard/share/email")
@login_required
@module_required("cv")
def share_vcard_email():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBVCardShare.query.filter_by(vcard_id=vcard.vcard_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("cv.share_vcard"))

    s = RBVCardShare(
        vcard_id=vcard.vcard_id,
        owner_user_id=me_id,
        target_user_id=None,
        target_email=email,
        share_token=make_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_vcard"))


# ─────────────────────────────
# CV files (PDF upload)
# ─────────────────────────────
@cv_bp.post("/cvfile/new")
@login_required
@module_required("cv")
def cvfile_new():
    me_id = get_current_user_id()

    cv_name = (request.form.get("cv_name") or "").strip()
    if not cv_name:
        abort(400, "CV name required")

    f = request.files.get("pdf")
    if not f or not f.filename:
        abort(400, "PDF required")

    if not allowed_pdf(f.filename, getattr(f, "mimetype", None)):
        abort(400, "Only PDF files are allowed")

    safe = sanitize_filename(f.filename)
    stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe}"
    out_dir = _cv_user_dir(me_id)
    stored_path = out_dir / stored_name
    f.save(stored_path)

    size_bytes = stored_path.stat().st_size

    rec = RBCVFile(
        owner_user_id=me_id,
        cv_name=cv_name,
        original_filename=safe,
        stored_path=str(stored_path),
        mime_type="application/pdf",
        size_bytes=size_bytes,
    )
    db.session.add(rec)
    db.session.commit()

    return redirect(url_for("cv.home"))


@cv_bp.post("/cvfile/<int:cvfile_id>/delete")
@login_required
@module_required("cv")
def cvfile_delete(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    # best effort remove file
    try:
        if c.stored_path and os.path.exists(c.stored_path):
            os.remove(c.stored_path)
    except Exception:
        pass

    # delete shares
    RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id).delete()

    db.session.delete(c)
    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.get("/cvfile/<int:cvfile_id>/share")
@login_required
@module_required("cv")
def share_cvfile(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    shares = (
        RBCVFileShare.query
        .filter_by(cvfile_id=cvfile_id, owner_user_id=me_id)
        .order_by(RBCVFileShare.created_at.desc())
        .all()
    )
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()

    public_share = next((s for s in shares if s.is_public), None)
    public_link = url_for("cvviewer.view", token=public_share.share_token, _external=True) if public_share else None

    return render_template("cv/share_cvfile.html", c=c, shares=shares, users=users, public_link=public_link)


@cv_bp.post("/cvfile/<int:cvfile_id>/share/public")
@login_required
@module_required("cv")
def share_cvfile_public(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    s = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, is_public=True).first()
    if not s:
        s = RBCVFileShare(
            cvfile_id=cvfile_id,
            owner_user_id=me_id,
            target_user_id=None,
            target_email=None,
            share_token=make_token(),
            is_public=True,
        )
        db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))


@cv_bp.post("/cvfile/<int:cvfile_id>/share/user")
@login_required
@module_required("cv")
def share_cvfile_user(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")
    target_user_id = int(target_user_id)

    exists = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))

    s = RBCVFileShare(
        cvfile_id=cvfile_id,
        owner_user_id=me_id,
        target_user_id=target_user_id,
        target_email=None,
        share_token=make_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))


@cv_bp.post("/cvfile/<int:cvfile_id>/share/email")
@login_required
@module_required("cv")
def share_cvfile_email(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))

    s = RBCVFileShare(
        cvfile_id=cvfile_id,
        owner_user_id=me_id,
        target_user_id=None,
        target_email=email,
        share_token=make_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))


# ─────────────────────────────
# Viewers
# ─────────────────────────────
@cvviewer_bp.get("/<token>")
def view(token: str):
    s = RBCVFileShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        abort(403)

    c = RBCVFile.query.get_or_404(s.cvfile_id)
    owner = RBUser.query.get(c.owner_user_id)
    return render_template("cv/view_public_cv.html", c=c, owner=owner, share=s)


@cvviewer_bp.get("/file/<token>")
def file(token: str):
    s = RBCVFileShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        abort(403)

    c = RBCVFile.query.get_or_404(s.cvfile_id)
    if not c.stored_path or not os.path.exists(c.stored_path):
        abort(404)

    return send_file(
        c.stored_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=c.original_filename or "cv.pdf",
        conditional=True,
    )


@vcardviewer_bp.get("/<token>")
def view(token: str):
    s = RBVCardShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        abort(403)

    v = RBVCard.query.get_or_404(s.vcard_id)
    skills, services = _vcard_items(v.vcard_id)
    owner = RBUser.query.get(v.user_id)
    return render_template("cv/view_public_vcard.html", vcard=v, skills=skills, services=services, owner=owner, share=s)
