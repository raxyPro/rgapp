from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, abort, redirect, render_template, request, url_for, send_file, current_app, flash
from flask_login import login_required, current_user

from extensions import db
from models import RBUser, RBUserProfile
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.cv.models import (
    RBVCard,
    RBVCardItem,
    RBCVFile,
    RBVCardShare,
    RBCVFileShare,
    RBCVPair,
    RBCVShare,
    RBCVPublicLink,
)
from modules.cv.util import make_token, sanitize_filename, allowed_pdf
from werkzeug.security import generate_password_hash


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


def _job_pref_from_vcard(v: RBVCard) -> str:
    parts = []
    if v.location:
        parts.append(f"Location: {v.location}")
    if v.work_mode:
        label = "Work from office" if v.work_mode == "wfo" else ("Hybrid" if v.work_mode == "hybrid" else "Remote")
        parts.append(f"Mode: {label}")
    if v.city:
        parts.append(f"City: {v.city}")
    if v.available_from:
        parts.append(f"Available from: {v.available_from}")
    if v.hours_per_day:
        parts.append(f"Hours/day: {v.hours_per_day}")
    return "; ".join(parts)


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


def _render_onepage_html(p: RBCVPair) -> str:
    """Generate a simple one-page HTML snippet from pair fields."""
    sections = [
        f"<h2>{p.op_name or p.v_name}</h2>",
        f"<p><strong>Email:</strong> {p.op_email or p.v_email} | <strong>Phone:</strong> {p.op_phone or p.v_phone}</p>",
        f"<p><strong>Title:</strong> {p.op_title}</p>",
        f"<p><strong>LinkedIn:</strong> {(p.op_linkedin_url or p.v_linkedin_url or '')}</p>",
        f"<p><strong>Website:</strong> {p.op_website_url or ''}</p>",
        "<hr/>",
        f"<h4>About</h4><p>{p.op_about or ''}</p>",
        f"<h4>Skills</h4><p>{p.op_skills or ''}</p>",
        f"<h4>Experience</h4><p>{p.op_experience or ''}</p>",
        f"<h4>Academic</h4><p>{p.op_academic or ''}</p>",
        f"<h4>Achievements</h4><p>{p.op_achievements or ''}</p>",
        f"<h4>Final Remarks</h4><p>{p.op_final_remark or ''}</p>",
    ]
    return "\n".join(sections)


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
    pair_shares = (
        RBCVShare.query
        .filter((RBCVShare.target_user_id == me_id) | (RBCVShare.target_email == me_email))
        .order_by(RBCVShare.created_at.desc())
        .all()
    )

    # Owners for display
    owner_ids = list({s.owner_user_id for s in (vcard_shares + cvfile_shares + pair_shares)})
    owners = {u.user_id: u for u in RBUser.query.filter(RBUser.user_id.in_(owner_ids)).all()} if owner_ids else {}
    if owners:
        profs = RBUserProfile.query.filter(RBUserProfile.user_id.in_(owners.keys())).all()
        for p in profs:
            if p.user_id in owners:
                owners[p.user_id].handle = p.handle

    # Assets maps
    shared_vcard_ids = list({s.vcard_id for s in vcard_shares})
    shared_vcards = {v.vcard_id: v for v in RBVCard.query.filter(RBVCard.vcard_id.in_(shared_vcard_ids)).all()} if shared_vcard_ids else {}

    shared_cvfile_ids = list({s.cvfile_id for s in cvfile_shares})
    shared_cvfiles = {c.cvfile_id: c for c in RBCVFile.query.filter(RBCVFile.cvfile_id.in_(shared_cvfile_ids)).all()} if shared_cvfile_ids else {}

    shared_pair_ids = list({s.cv_id for s in pair_shares})
    shared_pairs = {p.cv_id: p for p in RBCVPair.query.filter(RBCVPair.cv_id.in_(shared_pair_ids)).all()} if shared_pair_ids else {}

    return render_template(
        "cv/home.html",
        vcard=vcard,
        skills=skills,
        services=services,
        cv_files=cv_files,
        vcard_shares=vcard_shares,
        cvfile_shares=cvfile_shares,
        pair_shares=pair_shares,
        owners=owners,
        shared_vcards=shared_vcards,
        shared_cvfiles=shared_cvfiles,
        shared_pairs=shared_pairs,
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
    vcard.location = (request.form.get("location") or "").strip() or None
    vcard.work_mode = (request.form.get("work_mode") or "").strip() or None
    vcard.city = (request.form.get("city") or "").strip() or None
    avail = (request.form.get("available_from") or "").strip()
    vcard.available_from = datetime.strptime(avail, "%Y-%m-%d").date() if avail else None
    hrs = request.form.get("hours_per_day")
    try:
        vcard.hours_per_day = int(hrs) if hrs else None
    except ValueError:
        vcard.hours_per_day = None
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


@cv_bp.post("/pair/new")
@login_required
@module_required("cv")
def pair_new():
    me_id = get_current_user_id()
    # Blank online CV
    p = RBCVPair(
        user_id=me_id,
        v_name="",
        v_company="",
        v_email="",
        v_phone="",
        v_primary_skill="",
        v_skill_description="",
        v_organizations="",
        v_achievements="",
        op_name="",
        op_email="",
        op_phone="",
        op_title="",
        op_linkedin_url="",
        op_website_url="",
        op_about="",
        op_skills="",
        op_experience="",
        op_academic="",
        op_achievements="",
        op_final_remark="",
    )
    p.onepage_html = _render_onepage_html(p)
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.get("/pair/<int:cv_id>/edit")
@login_required
@module_required("cv")
def pair_edit(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)
    return render_template("cv/edit_pair.html", pair=p)


@cv_bp.post("/pair/<int:cv_id>/edit")
@login_required
@module_required("cv")
def pair_save(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)

    # vCard-like fields
    p.v_name = (request.form.get("v_name") or "").strip()
    p.v_company = (request.form.get("v_company") or "").strip()
    p.v_email = (request.form.get("v_email") or "").strip()
    p.v_phone = (request.form.get("v_phone") or "").strip()
    p.v_primary_skill = (request.form.get("v_primary_skill") or "").strip()
    p.v_skill_description = (request.form.get("v_skill_description") or "").strip()
    p.v_organizations = (request.form.get("v_organizations") or "").strip()
    p.v_achievements = (request.form.get("v_achievements") or "").strip()

    # One-page sections
    p.op_name = (request.form.get("op_name") or "").strip()
    p.op_email = (request.form.get("op_email") or "").strip()
    p.op_phone = (request.form.get("op_phone") or "").strip()
    p.op_title = (request.form.get("op_title") or "").strip()
    p.op_linkedin_url = (request.form.get("op_linkedin_url") or "").strip()
    p.op_website_url = (request.form.get("op_website_url") or "").strip()
    p.op_about = (request.form.get("op_about") or "").strip()
    p.op_skills = (request.form.get("op_skills") or "").strip()
    p.op_experience = (request.form.get("op_experience") or "").strip()
    p.op_academic = (request.form.get("op_academic") or "").strip()
    p.op_achievements = (request.form.get("op_achievements") or "").strip()
    p.op_final_remark = (request.form.get("op_final_remark") or "").strip()

    p.onepage_html = _render_onepage_html(p)
    p.updated_at = datetime.utcnow()
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.post("/pair/<int:cv_id>/archive")
@login_required
@module_required("cv")
def pair_archive(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)
    p.is_archived = True
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("cv.home"))


@cv_bp.post("/pair/<int:cv_id>/unarchive")
@login_required
@module_required("cv")
def pair_unarchive(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)
    p.is_archived = False
    db.session.add(p)
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
    vcard = _get_or_create_vcard(me_id)

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

    # Optional cover letter PDF
    cover_file = request.files.get("cover_pdf")
    cover_path = cover_name = cover_mime = None
    cover_size = None
    if cover_file and cover_file.filename:
        if not allowed_pdf(cover_file.filename, getattr(cover_file, "mimetype", None)):
            abort(400, "Cover letter must be PDF")
        cover_safe = sanitize_filename(cover_file.filename)
        cover_stored = out_dir / f"cover_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{cover_safe}"
        cover_file.save(cover_stored)
        cover_path = str(cover_stored)
        cover_name = cover_safe
        cover_mime = "application/pdf"
        cover_size = cover_stored.stat().st_size

    rec = RBCVFile(
        owner_user_id=me_id,
        cv_name=cv_name,
        cover_letter=(request.form.get("cover_letter") or "").strip() or None,
        job_pref=(request.form.get("job_pref") or "").strip() or _job_pref_from_vcard(vcard) or None,
        cover_letter_path=cover_path,
        cover_letter_name=cover_name,
        cover_letter_mime=cover_mime,
        cover_letter_size=cover_size,
        original_filename=safe,
        stored_path=str(stored_path),
        mime_type="application/pdf",
        size_bytes=size_bytes,
    )
    db.session.add(rec)
    db.session.commit()

    return redirect(url_for("cv.home"))


@cv_bp.post("/cvfile/<int:cvfile_id>/edit")
@login_required
@module_required("cv")
def cvfile_edit(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    cv_name = (request.form.get("cv_name") or "").strip()
    if not cv_name:
        abort(400, "CV name required")

    file = request.files.get("pdf")
    if file and file.filename:
        if not allowed_pdf(file.filename, getattr(file, "mimetype", None)):
            abort(400, "Only PDF files are allowed")
        safe = sanitize_filename(file.filename)
        stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe}"
        out_dir = _cv_user_dir(me_id)
        stored_path = out_dir / stored_name
        file.save(stored_path)
        c.stored_path = str(stored_path)
        c.original_filename = safe
        c.mime_type = "application/pdf"
        c.size_bytes = stored_path.stat().st_size

    cover_file = request.files.get("cover_pdf")
    if cover_file and cover_file.filename:
        if not allowed_pdf(cover_file.filename, getattr(cover_file, "mimetype", None)):
            abort(400, "Cover letter must be PDF")
        cover_safe = sanitize_filename(cover_file.filename)
        out_dir = _cv_user_dir(me_id)
        cover_stored = out_dir / f"cover_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{cover_safe}"
        cover_file.save(cover_stored)
        # Best effort remove old cover
        try:
            if c.cover_letter_path and os.path.exists(c.cover_letter_path):
                os.remove(c.cover_letter_path)
        except Exception:
            pass
        c.cover_letter_path = str(cover_stored)
        c.cover_letter_name = cover_safe
        c.cover_letter_mime = "application/pdf"
        c.cover_letter_size = cover_stored.stat().st_size

    c.cv_name = cv_name
    c.cover_letter = (request.form.get("cover_letter") or c.cover_letter or "").strip() or None
    c.job_pref = (request.form.get("job_pref") or c.job_pref or "").strip() or None
    c.touch()
    db.session.add(c)
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


@cv_bp.get("/cvfile/<int:cvfile_id>/view")
@login_required
@module_required("cv")
def cvfile_view(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)
    if not c.stored_path or not os.path.exists(c.stored_path):
        abort(404)
    return send_file(
        c.stored_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=c.original_filename or "cv.pdf",
        conditional=True,
    )


@cv_bp.get("/cvfile/<int:cvfile_id>/cover")
@login_required
@module_required("cv")
def cvfile_cover_view(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)
    if not c.cover_letter_path or not os.path.exists(c.cover_letter_path):
        abort(404)
    return send_file(
        c.cover_letter_path,
        mimetype=c.cover_letter_mime or "application/pdf",
        as_attachment=False,
        download_name=c.cover_letter_name or "cover-letter.pdf",
        conditional=True,
    )


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

    # Existing public links list
    public_links = (
        RBCVPublicLink.query
        .filter_by(cvfile_id=cvfile_id)
        .order_by(RBCVPublicLink.created_at.desc())
        .all()
    )

    now = datetime.utcnow()
    public_links_view = []
    for pl in public_links:
        status = pl.status
        if status == "active" and pl.expires_at and pl.expires_at <= now:
            status = "expired"
        rem_secs = None
        if pl.expires_at:
            rem_secs = int((pl.expires_at - now).total_seconds())
        public_links_view.append({"obj": pl, "status": status, "rem_secs": rem_secs})

    return render_template("cv/share_cvfile.html", c=c, shares=shares, users=users, public_links=public_links_view)


@cv_bp.post("/cvfile/<int:cvfile_id>/share/<int:share_id>/delete")
@login_required
@module_required("cv")
def delete_cvfile_share(cvfile_id: int, share_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    share = RBCVFileShare.query.get_or_404(share_id)
    if share.owner_user_id != me_id or share.cvfile_id != cvfile_id:
        abort(403)

    db.session.delete(share)
    db.session.commit()
    flash("Share deleted.", "info")
    return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))


@cv_bp.get("/pair/<int:cv_id>/share")
@login_required
@module_required("cv")
def share_pair(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)

    shares = (
        RBCVShare.query
        .filter_by(cv_id=cv_id, owner_user_id=me_id)
        .order_by(RBCVShare.created_at.desc())
        .all()
    )
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()

    public_share = next((s for s in shares if s.is_public), None)
    public_link = url_for("cvviewer.view_pair", token=public_share.share_token, _external=True) if public_share else None

    return render_template("cv/share_pair.html", pair=p, shares=shares, users=users, public_link=public_link)


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


@cv_bp.post("/cvfile/<int:cvfile_id>/public-link")
@login_required
@module_required("cv")
def create_public_link(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVFile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id:
        abort(403)

    name = (request.form.get("name") or "").strip()
    minutes_raw = int(request.form.get("expiry_minutes") or 15)
    minutes = max(0, min(1440, minutes_raw))
    share_type = request.form.get("share_type") or "public"
    target = (request.form.get("target") or "").strip() or None
    allow_download = request.form.get("allow_download") == "true"
    pw = (request.form.get("password") or "").strip()
    pw_hash = generate_password_hash(pw) if pw else None

    token = make_token()
    expires_at = datetime.utcnow() + timedelta(minutes=minutes) if minutes > 0 else None
    link = RBCVPublicLink(
        cvfile_id=c.cvfile_id,
        created_by=me_id,
        name=name or None,
        share_type=share_type,
        target=target,
        token=token,
        allow_download=allow_download,
        password_hash=pw_hash,
        expires_at=expires_at,
        status="active",
    )
    db.session.add(link)
    db.session.commit()
    flash("Public link created.", "success")
    return redirect(url_for("cv.share_cvfile", cvfile_id=cvfile_id))


@cv_bp.post("/cvfile/public-link/<int:link_id>/extend")
@login_required
@module_required("cv")
def extend_public_link(link_id: int):
    me_id = get_current_user_id()
    link = RBCVPublicLink.query.get_or_404(link_id)
    cv = RBCVFile.query.get_or_404(link.cvfile_id)
    if cv.owner_user_id != me_id:
        abort(403)
    link.expires_at = (link.expires_at or datetime.utcnow()) + timedelta(minutes=10)
    db.session.add(link)
    db.session.commit()
    flash("Link extended +10 minutes.", "success")
    return redirect(url_for("cv.share_cvfile", cvfile_id=cv.cvfile_id))


@cv_bp.post("/cvfile/public-link/<int:link_id>/disable")
@login_required
@module_required("cv")
def disable_public_link(link_id: int):
    me_id = get_current_user_id()
    link = RBCVPublicLink.query.get_or_404(link_id)
    cv = RBCVFile.query.get_or_404(link.cvfile_id)
    if cv.owner_user_id != me_id:
        abort(403)
    link.status = "disabled"
    db.session.add(link)
    db.session.commit()
    flash("Link disabled.", "info")
    return redirect(url_for("cv.share_cvfile", cvfile_id=cv.cvfile_id))


@cv_bp.post("/cvfile/public-link/<int:link_id>/delete")
@login_required
@module_required("cv")
def delete_public_link(link_id: int):
    me_id = get_current_user_id()
    link = RBCVPublicLink.query.get_or_404(link_id)
    cv = RBCVFile.query.get_or_404(link.cvfile_id)
    if cv.owner_user_id != me_id:
        abort(403)
    db.session.delete(link)
    db.session.commit()
    flash("Link deleted.", "info")
    return redirect(url_for("cv.share_cvfile", cvfile_id=cv.cvfile_id))


@cv_bp.post("/pair/<int:cv_id>/share/public")
@login_required
@module_required("cv")
def share_pair_public(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)

    s = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, is_public=True).first()
    if not s:
        s = RBCVShare(
            cv_id=cv_id,
            owner_user_id=me_id,
            target_user_id=None,
            target_email=None,
            share_token=make_token(),
            is_public=True,
        )
        db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_pair", cv_id=cv_id))


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


@cv_bp.post("/pair/<int:cv_id>/share/user")
@login_required
@module_required("cv")
def share_pair_user(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")
    target_user_id = int(target_user_id)

    exists = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("cv.share_pair", cv_id=cv_id))

    s = RBCVShare(
        cv_id=cv_id,
        owner_user_id=me_id,
        target_user_id=target_user_id,
        target_email=None,
        share_token=make_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_pair", cv_id=cv_id))


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


@cv_bp.post("/pair/<int:cv_id>/share/email")
@login_required
@module_required("cv")
def share_pair_email(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        abort(403)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("cv.share_pair", cv_id=cv_id))

    s = RBCVShare(
        cv_id=cv_id,
        owner_user_id=me_id,
        target_user_id=None,
        target_email=email,
        share_token=make_token(),
        is_public=False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("cv.share_pair", cv_id=cv_id))


# ─────────────────────────────
# Viewers
# ─────────────────────────────
@cvviewer_bp.route("/<token>", methods=["GET", "POST"])
def view(token: str):
    from flask import session, render_template_string
    s = RBCVFileShare.query.filter_by(share_token=token).first()
    if s:
        # Token grants access whether public or private
        c = RBCVFile.query.get_or_404(s.cvfile_id)
        owner = RBUser.query.get(c.owner_user_id)
        cv_link = url_for("cvviewer.view", token=s.share_token, _external=True)
        return render_template("cv/view_public_cv.html", c=c, owner=owner, share=s, cv_link=cv_link)

    pl = RBCVPublicLink.query.filter_by(token=token).first_or_404()
    if pl.status != "active":
        abort(403)
    if pl.expires_at and pl.expires_at <= datetime.utcnow():
        abort(410)
    # Password check
    if pl.password_hash:
        key = f"cv_pl_ok_{pl.token}"
        if not session.get(key):
            if request.method == "POST":
                pw = (request.form.get("password") or "").strip()
                from werkzeug.security import check_password_hash
                if pw and check_password_hash(pl.password_hash, pw):
                    session[key] = True
                else:
                    return render_template("cv/view_public_cv.html", c=None, owner=None, share=pl, cv_link=None, need_password=True, error="Invalid password"), 403
            else:
                return render_template("cv/view_public_cv.html", c=None, owner=None, share=pl, cv_link=None, need_password=True)
    c = RBCVFile.query.get_or_404(pl.cvfile_id)
    owner = RBUser.query.get(c.owner_user_id)
    cv_link = url_for("cvviewer.view", token=pl.token, _external=True)
    return render_template("cv/view_public_cv.html", c=c, owner=owner, share=pl, cv_link=cv_link, need_password=False)


@cvviewer_bp.get("/file/<token>")
def file(token: str):
    s = RBCVFileShare.query.filter_by(share_token=token).first()
    if s:
        c = RBCVFile.query.get_or_404(s.cvfile_id)
        allow_dl = True
    else:
        pl = RBCVPublicLink.query.filter_by(token=token).first_or_404()
        if pl.status != "active":
            abort(403)
        if pl.expires_at and pl.expires_at <= datetime.utcnow():
            abort(410)
        c = RBCVFile.query.get_or_404(pl.cvfile_id)
        allow_dl = pl.allow_download

    if not c.stored_path or not os.path.exists(c.stored_path):
        abort(404)

    return send_file(
        c.stored_path,
        mimetype="application/pdf",
        as_attachment=allow_dl,
        download_name=c.original_filename or "cv.pdf",
        conditional=True,
    )


@cvviewer_bp.get("/cover/<token>")
def cover(token: str):
    s = RBCVFileShare.query.filter_by(share_token=token).first()
    if s:
        c = RBCVFile.query.get_or_404(s.cvfile_id)
    else:
        pl = RBCVPublicLink.query.filter_by(token=token).first_or_404()
        if pl.status != "active":
            abort(403)
        if pl.expires_at and pl.expires_at <= datetime.utcnow():
            abort(410)
        c = RBCVFile.query.get_or_404(pl.cvfile_id)

    if not c.cover_letter_path or not os.path.exists(c.cover_letter_path):
        abort(404)

    return send_file(
        c.cover_letter_path,
        mimetype=c.cover_letter_mime or "application/pdf",
        as_attachment=False,
        download_name=c.cover_letter_name or "cover-letter.pdf",
        conditional=True,
    )


@cvviewer_bp.get("/pair/<token>")
def view_pair(token: str):
    s = RBCVShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        abort(403)

    p = RBCVPair.query.get_or_404(s.cv_id)
    owner = RBUser.query.get(p.user_id)
    return render_template("cv/view_public_pair.html", pair=p, owner=owner, share=s)


@vcardviewer_bp.get("/<token>")
def view(token: str):
    s = RBVCardShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        abort(403)

    v = RBVCard.query.get_or_404(s.vcard_id)
    skills, services = _vcard_items(v.vcard_id)
    owner = RBUser.query.get(v.user_id)
    return render_template("cv/view_public_vcard.html", vcard=v, skills=skills, services=services, owner=owner, share=s)
