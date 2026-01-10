from __future__ import annotations

from datetime import datetime, timedelta
import json
from inspect import signature
from io import BytesIO

from flask import Blueprint, abort, redirect, render_template, request, url_for, send_file, flash, current_app
from flask_login import login_required

from extensions import db
from models import RBUser, RBUserProfile
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.profiles.models import (
    RBCVProfile,
    RBVCardShare,
    RBCVFileShare,
    RBCVPair,
    RBCVShare,
    RBCVPublicLink,
)
from modules.profiles.service_profile import (
    _current_user_email_lower,
    _log_event,
    _forbidden,
    _log_access,
    _get_or_create_vcard,
    _job_pref_from_vcard,
    _job_pref_from_fields,
    _vcard_items,
    _get_cv_profile,
    _find_user_by_handle,
    _cv_name_exists,
    _render_onepage_html,
    _can_access_share_target,
    build_vcard_export,
    log_profile_action,
)
from models import RBAudit
import uuid
from modules.profiles.util import make_token, sanitize_filename, allowed_pdf
from werkzeug.security import generate_password_hash


profiles_bp = Blueprint(
    "profiles",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/profiles",
)

profileviewer_bp = Blueprint(
    "profileviewer",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/profileviewer",
)

vcardviewer_bp = Blueprint(
    "vcardviewer",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/vcardviewer",
)


_SEND_FILE_NAME_PARAM = (
    "download_name"
    if "download_name" in signature(send_file).parameters
    else "attachment_filename"
)


def _send_file_named(fileobj, filename: str, **kwargs):
    safe_name = sanitize_filename(filename or "cv.pdf")
    kwargs[_SEND_FILE_NAME_PARAM] = safe_name
    return send_file(fileobj, **kwargs)


def _send_bytes(data: bytes, filename: str, mimetype: str, as_attachment: bool):
    safe_name = sanitize_filename(filename or "cv.pdf")
    resp = current_app.response_class(data, mimetype=mimetype)
    disp = "attachment" if as_attachment else "inline"
    resp.headers["Content-Disposition"] = f'{disp}; filename="{safe_name}"'
    resp.headers["Content-Length"] = str(len(data))
    return resp


@profiles_bp.get("/")
@login_required
@module_required("profiles")
def home():
    print("Profiles Home accessed")
    me_id = get_current_user_id()
    me_email = _current_user_email_lower()

    vcard = _get_or_create_vcard(me_id)
    skills, services = _vcard_items(vcard.vcard_id)

    cv_files = (
        RBCVProfile.query
        .filter_by(owner_user_id=me_id, is_archived=False, doc_type="cv")
        .order_by(RBCVProfile.updated_at.desc())
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
    shared_vcards = {
        v.vcard_id: v
        for v in RBCVProfile.query.filter(
            RBCVProfile.vcard_id.in_(shared_vcard_ids),
            RBCVProfile.doc_type == "vcard",
        ).all()
    } if shared_vcard_ids else {}

    shared_cvfile_ids = list({s.cvfile_id for s in cvfile_shares})
    shared_cvfiles = {
        c.cvfile_id: c
        for c in RBCVProfile.query.filter(
            RBCVProfile.vcard_id.in_(shared_cvfile_ids),
            RBCVProfile.doc_type == "cv",
        ).all()
    } if shared_cvfile_ids else {}

    # Shares created by me
    own_cvfile_ids = [c.cvfile_id for c in cv_files] if cv_files else []
    my_shares = (
        RBCVFileShare.query
        .filter(RBCVFileShare.owner_user_id == me_id)
        .filter(RBCVFileShare.cvfile_id.in_(own_cvfile_ids) if own_cvfile_ids else False)
        .order_by(RBCVFileShare.created_at.desc())
        .all()
    ) if own_cvfile_ids else []
    my_public_links = (
        RBCVPublicLink.query
        .filter(RBCVPublicLink.created_by == me_id)
        .filter(RBCVPublicLink.cvfile_id.in_(own_cvfile_ids) if own_cvfile_ids else False)
        .order_by(RBCVPublicLink.created_at.desc())
        .all()
    ) if own_cvfile_ids else []
    share_user_ids = [s.target_user_id for s in my_shares if s.target_user_id] if my_shares else []
    share_users = {u.user_id: u for u in RBUser.query.filter(RBUser.user_id.in_(share_user_ids)).all()} if share_user_ids else {}
    share_profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(share_user_ids)).all()} if share_user_ids else {}

    shared_pair_ids = list({s.cv_id for s in pair_shares})
    shared_pairs = {p.cv_id: p for p in RBCVPair.query.filter(RBCVPair.cv_id.in_(shared_pair_ids)).all()} if shared_pair_ids else {}

    return render_template(
        "profiles/home.html",
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
        my_shares=my_shares,
        my_public_links=my_public_links,
        share_users=share_users,
        share_profiles=share_profiles,
    )


# ─────────────────────────────
# vCard edit
# ─────────────────────────────
@profiles_bp.get("/vcard/edit")
@login_required
@module_required("profiles")
def edit_vcard():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)
    skills, services = _vcard_items(vcard.vcard_id)
    return render_template("profiles/edit_vcard.html", vcard=vcard, skills=skills, services=services)


@profiles_bp.post("/vcard/edit")
@login_required
@module_required("profiles")
def save_vcard():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)
    prev_details = dict(vcard.details or {})

    vcard.name = (request.form.get("name") or "").strip()
    vcard.email = (request.form.get("email") or "").strip()
    vcard.linkedin_url = (request.form.get("linkedin_url") or "").strip()
    vcard.phone = (request.form.get("phone") or "").strip()
    vcard.tagline = (request.form.get("tagline") or "").strip()
    vcard.location = (request.form.get("location") or "").strip() or None
    vcard.work_mode = (request.form.get("work_mode") or "").strip() or None
    vcard.city = (request.form.get("city") or "").strip() or None
    avail = (request.form.get("available_from") or "").strip()
    vcard.available_from = avail if avail else None
    hrs = request.form.get("hours_per_day")
    try:
        vcard.hours_per_day = int(hrs) if hrs else None
    except ValueError:
        vcard.hours_per_day = None
    vcard.job_pref_loc = (request.form.get("job_pref_loc") or "").strip() or None
    vcard.job_pref_mode = (request.form.get("job_pref_mode") or "").strip() or None
    vcard.job_pref_city = (request.form.get("job_pref_city") or "").strip() or None
    pref_hrs = request.form.get("job_pref_hours")
    try:
        vcard.job_pref_hours = int(pref_hrs) if pref_hrs else None
    except ValueError:
        vcard.job_pref_hours = None
    vcard.touch()

    skills = []
    services = []

    def _ingest(kind: str, titles, descs, exps, target_list):
        for idx, t in enumerate(titles):
            title = (t or "").strip()
            if not title:
                continue
            desc = (descs[idx] if idx < len(descs) else "") or ""
            exp = (exps[idx] if idx < len(exps) else "") or ""
            target_list.append(
                {
                    "item_type": kind,
                    "title": title.strip(),
                    "description": desc.strip(),
                    "experience": exp.strip(),
                    "sort_order": idx,
                }
            )

    _ingest(
        "skill",
        request.form.getlist("skill_title[]"),
        request.form.getlist("skill_desc[]"),
        request.form.getlist("skill_exp[]"),
        skills,
    )
    _ingest(
        "service",
        request.form.getlist("service_title[]"),
        request.form.getlist("service_desc[]"),
        request.form.getlist("service_exp[]"),
        services,
    )

    vcard.skills = skills
    vcard.services = services

    db.session.add(vcard)
    db.session.add(
        RBAudit(
            event_id=str(uuid.uuid4()),
            tblname="rb_cv_profile",
            row_id=vcard.vcard_id,
            doc_type="vcard",
            action="edit",
            actor_id=me_id,
            source="self",
            prev_data=prev_details,
            new_data=vcard.details,
        )
    )
    log_profile_action(
        "vcard_save",
        "start",
        vcard_id=vcard.vcard_id,
        doc_type=vcard.doc_type,
        fields={
            "name": vcard.name,
            "email": vcard.email,
            "phone": vcard.phone,
            "linkedin_url": vcard.linkedin_url,
            "tagline": vcard.tagline,
            "location": vcard.location,
            "work_mode": vcard.work_mode,
            "city": vcard.city,
            "available_from": vcard.available_from,
            "hours_per_day": vcard.hours_per_day,
            "skills_count": len(skills),
            "services_count": len(services),
        },
    )
    try:
        db.session.commit()
    except Exception as exc:
        log_profile_action(
            "vcard_save",
            "error",
            vcard_id=vcard.vcard_id,
            error=str(exc),
        )
        raise
    log_profile_action(
        "vcard_save",
        "ok",
        vcard_id=vcard.vcard_id,
    )
    flash("vCard updated.", "success")
    return redirect(url_for("profiles.home"))


@profiles_bp.get("/vcard/download")
@login_required
@module_required("profiles")
def download_vcard_json():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)
    payload = build_vcard_export(vcard)
    data = json.dumps(payload, ensure_ascii=True, indent=2, default=str)
    payload_bytes = data.encode("utf-8")
    filename = f"vcard_{me_id}.json"
    log_profile_action(
        "vcard_download",
        "start",
        vcard_id=vcard.vcard_id,
        doc_type=vcard.doc_type,
        bytes=len(data),
    )
    try:
        resp = current_app.response_class(payload_bytes, mimetype="application/octet-stream")
        resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp.headers["Content-Length"] = str(len(payload_bytes))
        log_profile_action(
            "vcard_download",
            "ok",
            vcard_id=vcard.vcard_id,
            content_type=resp.headers.get("Content-Type"),
            content_disposition=resp.headers.get("Content-Disposition"),
            content_length=resp.calculate_content_length(),
        )
        return resp
    except Exception as exc:
        log_profile_action(
            "vcard_download",
            "error",
            vcard_id=vcard.vcard_id,
            error=str(exc),
        )
        raise


@profiles_bp.post("/pair/new")
@login_required
@module_required("profiles")
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
    return redirect(url_for("profiles.home"))


@profiles_bp.get("/pair/<int:cv_id>/edit")
@login_required
@module_required("profiles")
def pair_edit(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("pair_edit_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)
    _log_access("pair_edit_ok", cv_id=cv_id, me_id=me_id)
    return render_template("profiles/edit_pair.html", pair=p)


@profiles_bp.post("/pair/<int:cv_id>/edit")
@login_required
@module_required("profiles")
def pair_save(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("pair_save_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)

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
    return redirect(url_for("profiles.home"))


@profiles_bp.post("/pair/<int:cv_id>/archive")
@login_required
@module_required("profiles")
def pair_archive(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("pair_archive_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)
    p.is_archived = True
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("profiles.home"))


@profiles_bp.post("/pair/<int:cv_id>/unarchive")
@login_required
@module_required("profiles")
def pair_unarchive(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("pair_unarchive_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)
    p.is_archived = False
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("profiles.home"))


# ─────────────────────────────
# vCard sharing
# ─────────────────────────────
@profiles_bp.get("/vcard/share")
@login_required
@module_required("profiles")
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

    return render_template("profiles/share_vcard.html", vcard=vcard, shares=shares, users=users, public_link=public_link)


@profiles_bp.post("/vcard/share/public")
@login_required
@module_required("profiles")
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
    return redirect(url_for("profiles.share_vcard"))


@profiles_bp.post("/vcard/share/user")
@login_required
@module_required("profiles")
def share_vcard_user():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")
    target_user_id = int(target_user_id)

    exists = RBVCardShare.query.filter_by(vcard_id=vcard.vcard_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("profiles.share_vcard"))

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
    return redirect(url_for("profiles.share_vcard"))


@profiles_bp.post("/vcard/share/email")
@login_required
@module_required("profiles")
def share_vcard_email():
    me_id = get_current_user_id()
    vcard = _get_or_create_vcard(me_id)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBVCardShare.query.filter_by(vcard_id=vcard.vcard_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("profiles.share_vcard"))

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
    return redirect(url_for("profiles.share_vcard"))


# ─────────────────────────────
# CV files (PDF upload)
# ─────────────────────────────
@profiles_bp.post("/cvfile/new")
@login_required
@module_required("profiles")
def cvfile_new():
    me_id = get_current_user_id()

    cv_name = (request.form.get("cv_name") or "").strip()
    if not cv_name:
        abort(400, "CV name required")
    if _cv_name_exists(me_id, cv_name):
        flash("CV name must be unique.", "warning")
        return redirect(url_for("profiles.home"))
    vcard = _get_or_create_vcard(me_id)

    f = request.files.get("pdf")
    pdf_bytes = None
    safe = None
    size_bytes = None
    if f and f.filename:
        if not allowed_pdf(f.filename, getattr(f, "mimetype", None)):
            abort(400, "Only PDF files are allowed")
        safe = sanitize_filename(f.filename)
        pdf_bytes = f.read()
        size_bytes = len(pdf_bytes) if pdf_bytes else 0
        if size_bytes == 0:
            abort(400, "Empty PDF")

    # Optional cover letter PDF
    cover_file = request.files.get("cover_pdf")
    cover_name = cover_mime = None
    cover_size = None
    cover_bytes = None
    if cover_file and cover_file.filename:
        if not allowed_pdf(cover_file.filename, getattr(cover_file, "mimetype", None)):
            abort(400, "Cover letter must be PDF")
        cover_safe = sanitize_filename(cover_file.filename)
        cover_name = cover_safe
        cover_mime = "application/pdf"
        cover_bytes = cover_file.read()
        cover_size = len(cover_bytes) if cover_bytes else 0

    rec = RBCVProfile(
        user_id=me_id,
        doc_type="cv",
        details={
            "cv_name": cv_name,
            "cover_letter": (request.form.get("cover_letter") or "").strip() or None,
            "job_pref": (request.form.get("job_pref") or "").strip() or _job_pref_from_vcard(vcard) or None,
            "job_pref_loc": vcard.job_pref_loc or vcard.location,
            "job_pref_mode": vcard.job_pref_mode or vcard.work_mode,
            "job_pref_city": vcard.job_pref_city or vcard.city,
            "job_pref_hours": vcard.job_pref_hours or vcard.hours_per_day,
            "original_filename": safe,
            "cover_letter_name": cover_name,
            "cover_letter_mime": cover_mime,
            "cover_letter_size": cover_size,
        },
        pdf_data=pdf_bytes,
        pdf_name=safe,
        pdf_mime="application/pdf",
        pdf_size=size_bytes,
        cover_pdf_data=cover_bytes,
        cover_pdf_name=cover_name,
        cover_pdf_mime=cover_mime,
        cover_pdf_size=cover_size,
    )
    db.session.add(rec)
    db.session.commit()

    return redirect(url_for("profiles.home"))


@profiles_bp.post("/cvfile/<int:cvfile_id>/edit")
@login_required
@module_required("profiles")
def cvfile_edit(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVProfile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id or c.doc_type != "cv":
        _forbidden("cvfile_edit_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, doc_type=c.doc_type, me_id=me_id)

    cv_name = (request.form.get("cv_name") or "").strip()
    if not cv_name:
        abort(400, "CV name required")
    if _cv_name_exists(me_id, cv_name, exclude_id=cvfile_id):
        flash("CV name must be unique.", "warning")
        return redirect(url_for("profiles.home"))

    file = request.files.get("pdf")
    if file and file.filename:
        if not allowed_pdf(file.filename, getattr(file, "mimetype", None)):
            abort(400, "Only PDF files are allowed")
        safe = sanitize_filename(file.filename)
        pdf_bytes = file.read()
        c.pdf_data = pdf_bytes
        c.pdf_name = safe
        c.original_filename = safe
        c.mime_type = "application/pdf"
        c.size_bytes = len(pdf_bytes) if pdf_bytes else 0

    cover_file = request.files.get("cover_pdf")
    if cover_file and cover_file.filename:
        if not allowed_pdf(cover_file.filename, getattr(cover_file, "mimetype", None)):
            abort(400, "Cover letter must be PDF")
        cover_safe = sanitize_filename(cover_file.filename)
        cover_bytes = cover_file.read()
        c.cover_pdf_data = cover_bytes
        c.cover_pdf_name = cover_safe
        c.cover_letter_name = cover_safe
        c.cover_pdf_mime = "application/pdf"
        c.cover_letter_mime = "application/pdf"
        c.cover_pdf_size = len(cover_bytes) if cover_bytes else 0
        c.cover_letter_size = c.cover_pdf_size

    c.cv_name = cv_name
    c.cover_letter = (request.form.get("cover_letter") or c.cover_letter or "").strip() or None
    pref_loc = (request.form.get("job_pref_loc") or "").strip() or None
    pref_mode = (request.form.get("job_pref_mode") or "").strip() or None
    pref_city = (request.form.get("job_pref_city") or "").strip() or None
    pref_hours = (request.form.get("job_pref_hours") or "").strip() or None
    c.job_pref_loc = pref_loc
    c.job_pref_mode = pref_mode
    c.job_pref_city = pref_city
    try:
        c.job_pref_hours = int(pref_hours) if pref_hours else None
    except ValueError:
        c.job_pref_hours = None
    pref_text = _job_pref_from_fields(pref_loc, pref_mode, pref_city, pref_hours)
    c.job_pref = pref_text or (request.form.get("job_pref") or c.job_pref or "").strip() or None
    c.touch()
    db.session.add(c)
    db.session.commit()
    return redirect(url_for("profiles.home"))


@profiles_bp.post("/cvfile/<int:cvfile_id>/delete")
@login_required
@module_required("profiles")
def cvfile_delete(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVProfile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id or c.doc_type != "cv":
        _forbidden("cvfile_delete_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, doc_type=c.doc_type, me_id=me_id)

    # delete shares
    RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id).delete()

    db.session.delete(c)
    db.session.commit()
    return redirect(url_for("profiles.home"))


@profiles_bp.get("/cvfile/<int:cvfile_id>/view")
@login_required
@module_required("profiles")
def cvfile_view(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVProfile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id or c.doc_type != "cv":
        _forbidden("cvfile_view_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, doc_type=c.doc_type, me_id=me_id)
    _log_access("cvfile_view_ok", cvfile_id=cvfile_id, me_id=me_id, download=False)
    if not c.pdf_data:
        abort(404)
    return _send_bytes(
        c.pdf_data,
        c.original_filename or "cv.pdf",
        c.mime_type or "application/pdf",
        as_attachment=False,
    )


@profiles_bp.get("/cvfile/<int:cvfile_id>/cover")
@login_required
@module_required("profiles")
def cvfile_cover_view(cvfile_id: int):
    me_id = get_current_user_id()
    c = RBCVProfile.query.get_or_404(cvfile_id)
    if c.owner_user_id != me_id or c.doc_type != "cv":
        _forbidden("cvfile_cover_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, doc_type=c.doc_type, me_id=me_id)
    _log_access("cvfile_cover_ok", cvfile_id=cvfile_id, me_id=me_id)
    if not c.cover_pdf_data:
        abort(404)
    return _send_bytes(
        c.cover_pdf_data,
        c.cover_letter_name or "cover-letter.pdf",
        c.cover_letter_mime or "application/pdf",
        as_attachment=False,
    )


@profiles_bp.get("/cvfile/<int:cvfile_id>/share")
@login_required
@module_required("profiles")
def share_cvfile(cvfile_id: int):
    me_id = get_current_user_id()
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("share_cvfile_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

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

    return render_template("profiles/share_cvfile.html", c=c, shares=shares, users=users, public_links=public_links_view)


@profiles_bp.post("/cvfile/<int:cvfile_id>/share/<int:share_id>/delete")
@login_required
@module_required("profiles")
def delete_cvfile_share(cvfile_id: int, share_id: int):
    me_id = get_current_user_id()
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("delete_cvfile_share_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

    share = RBCVFileShare.query.get_or_404(share_id)
    if share.owner_user_id != me_id or share.cvfile_id != cvfile_id:
        _forbidden("delete_cvfile_share_mismatch", cvfile_id=cvfile_id, owner=c.owner_user_id, share_owner=share.owner_user_id, share_cvfile_id=share.cvfile_id, me_id=me_id)

    db.session.delete(share)
    db.session.commit()
    flash("Share deleted.", "info")
    return redirect(url_for("profiles.home"))


@profiles_bp.get("/pair/<int:cv_id>/share")
@login_required
@module_required("profiles")
def share_pair(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("share_pair_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)

    shares = (
        RBCVShare.query
        .filter_by(cv_id=cv_id, owner_user_id=me_id)
        .order_by(RBCVShare.created_at.desc())
        .all()
    )
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()

    public_share = next((s for s in shares if s.is_public), None)
    public_link = url_for("profileviewer.view_pair", token=public_share.share_token, _external=True) if public_share else None

    return render_template("profiles/share_pair.html", pair=p, shares=shares, users=users, public_link=public_link)


@profiles_bp.post("/cvfile/<int:cvfile_id>/share/public")
@login_required
@module_required("profiles")
def share_cvfile_public(cvfile_id: int):
    me_id = get_current_user_id()
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("share_cvfile_public_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

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
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cvfile_id))


@profiles_bp.post("/cvfile/<int:cvfile_id>/public-link")
@login_required
@module_required("profiles")
def create_public_link(cvfile_id: int):
    me_id = get_current_user_id()
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("cv_public_link_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

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
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cvfile_id))


@profiles_bp.post("/cvfile/public-link/<int:link_id>/extend")
@login_required
@module_required("profiles")
def extend_public_link(link_id: int):
    me_id = get_current_user_id()
    link = RBCVPublicLink.query.get_or_404(link_id)
    cv = _get_cv_profile(link.cvfile_id)
    if cv.owner_user_id != me_id:
        _forbidden("cv_public_link_extend_not_owner", link_id=link_id, cvfile_id=cv.cvfile_id, owner=cv.owner_user_id, me_id=me_id)
    link.expires_at = (link.expires_at or datetime.utcnow()) + timedelta(minutes=10)
    db.session.add(link)
    db.session.commit()
    flash("Link extended +10 minutes.", "success")
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cv.cvfile_id))


@profiles_bp.post("/cvfile/public-link/<int:link_id>/disable")
@login_required
@module_required("profiles")
def disable_public_link(link_id: int):
    me_id = get_current_user_id()
    link = RBCVPublicLink.query.get_or_404(link_id)
    cv = _get_cv_profile(link.cvfile_id)
    if cv.owner_user_id != me_id:
        _forbidden("cv_public_link_disable_not_owner", link_id=link_id, cvfile_id=cv.cvfile_id, owner=cv.owner_user_id, me_id=me_id)
    link.status = "disabled"
    db.session.add(link)
    db.session.commit()
    flash("Link disabled.", "info")
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cv.cvfile_id))


@profiles_bp.post("/cvfile/public-link/<int:link_id>/delete")
@login_required
@module_required("profiles")
def delete_public_link(link_id: int):
    me_id = get_current_user_id()
    link = RBCVPublicLink.query.get_or_404(link_id)
    cv = _get_cv_profile(link.cvfile_id)
    if cv.owner_user_id != me_id:
        _forbidden("cv_public_link_delete_not_owner", link_id=link_id, cvfile_id=cv.cvfile_id, owner=cv.owner_user_id, me_id=me_id)
    db.session.delete(link)
    db.session.commit()
    flash("Link deleted.", "info")
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cv.cvfile_id))


@profiles_bp.post("/pair/<int:cv_id>/share/public")
@login_required
@module_required("profiles")
def share_pair_public(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("share_pair_public_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)

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
    return redirect(url_for("profiles.share_pair", cv_id=cv_id))


@profiles_bp.post("/cvfile/<int:cvfile_id>/share/user")
@login_required
@module_required("profiles")
def share_cvfile_user(cvfile_id: int):
    me_id = get_current_user_id()
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("share_cvfile_user_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")
    target_user_id = int(target_user_id)

    exists = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("profiles.share_cvfile", cvfile_id=cvfile_id))

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
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cvfile_id))


@profiles_bp.post("/pair/<int:cv_id>/share/user")
@login_required
@module_required("profiles")
def share_pair_user(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("share_pair_user_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)

    target_user_id = request.form.get("target_user_id")
    if not target_user_id or not str(target_user_id).isdigit():
        abort(400, "Select a user")
    target_user_id = int(target_user_id)

    exists = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, target_user_id=target_user_id).first()
    if exists:
        return redirect(url_for("profiles.share_pair", cv_id=cv_id))

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
    return redirect(url_for("profiles.share_pair", cv_id=cv_id))


@profiles_bp.post("/cvfile/<int:cvfile_id>/share/email")
@login_required
@module_required("profiles")
def share_cvfile_email(cvfile_id: int):
    me_id = get_current_user_id()
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("share_cvfile_email_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("profiles.share_cvfile", cvfile_id=cvfile_id))

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
    return redirect(url_for("profiles.share_cvfile", cvfile_id=cvfile_id))


@profiles_bp.post("/cvfile/share-new")
@login_required
@module_required("profiles")
def share_cvfile_new():
    me_id = get_current_user_id()
    cvfile_id = int(request.form.get("cvfile_id") or 0)
    c = _get_cv_profile(cvfile_id)
    if c.owner_user_id != me_id:
        _forbidden("share_cvfile_new_not_owner", cvfile_id=cvfile_id, owner=c.owner_user_id, me_id=me_id)

    share_method = (request.form.get("share_method") or "").strip()

    if share_method == "link":
        minutes_raw = int(request.form.get("expiry_minutes") or 15)
        minutes = max(0, min(1440, minutes_raw))
        pw = (request.form.get("password") or "").strip()
        pw_hash = generate_password_hash(pw) if pw else None
        token = make_token()
        expires_at = datetime.utcnow() + timedelta(minutes=minutes) if minutes > 0 else None
        link = RBCVPublicLink(
            cvfile_id=c.cvfile_id,
            created_by=me_id,
            name=None,
            share_type="public",
            target=None,
            token=token,
            allow_download=True,
            password_hash=pw_hash,
            expires_at=expires_at,
            status="active",
        )
        db.session.add(link)
        db.session.commit()
        flash("Public link created.", "success")
        return redirect(url_for("profiles.home"))

    if share_method == "handle":
        handle = (request.form.get("handle") or "").strip()
        target_user = _find_user_by_handle(handle)
        if not target_user:
            flash("Handle not found.", "warning")
            return redirect(url_for("profiles.home"))
        if target_user.user_id == me_id:
            flash("Cannot share with yourself.", "warning")
            return redirect(url_for("profiles.home"))
        exists = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, target_user_id=target_user.user_id).first()
        if exists:
            flash("Already shared with that user.", "info")
            return redirect(url_for("profiles.home"))
        s = RBCVFileShare(
            cvfile_id=cvfile_id,
            owner_user_id=me_id,
            target_user_id=target_user.user_id,
            target_email=None,
            share_token=make_token(),
            is_public=False,
        )
        db.session.add(s)
        db.session.commit()
        flash("Shared with user handle.", "success")
        return redirect(url_for("profiles.home"))

    if share_method == "email":
        email = (request.form.get("email") or "").strip().lower()
        if not email or "@" not in email:
            flash("Enter a valid email.", "warning")
            return redirect(url_for("profiles.home"))
        exists = RBCVFileShare.query.filter_by(cvfile_id=cvfile_id, owner_user_id=me_id, target_email=email).first()
        if exists:
            flash("Already shared with that email.", "info")
            return redirect(url_for("profiles.home"))
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
        # Email sending not wired; placeholder for integration.
        flash("Email share created.", "success")
        return redirect(url_for("profiles.home"))

    flash("Select a share method.", "warning")
    return redirect(url_for("profiles.home"))


@profiles_bp.post("/pair/<int:cv_id>/share/email")
@login_required
@module_required("profiles")
def share_pair_email(cv_id: int):
    me_id = get_current_user_id()
    p = RBCVPair.query.get_or_404(cv_id)
    if p.user_id != me_id:
        _forbidden("share_pair_email_not_owner", cv_id=cv_id, owner=p.user_id, me_id=me_id)

    email = (request.form.get("target_email") or "").strip().lower()
    if not email or "@" not in email:
        abort(400, "Enter a valid email")

    exists = RBCVShare.query.filter_by(cv_id=cv_id, owner_user_id=me_id, target_email=email).first()
    if exists:
        return redirect(url_for("profiles.share_pair", cv_id=cv_id))

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
    return redirect(url_for("profiles.share_pair", cv_id=cv_id))


# ─────────────────────────────
# Viewers
# ─────────────────────────────
@profileviewer_bp.route("/<token>", methods=["GET", "POST"])
def view(token: str):
    from flask import session
    s = RBCVFileShare.query.filter_by(share_token=token).first()
    if s:
        # Token grants access whether public or private
        c = _get_cv_profile(s.cvfile_id)
        owner = RBUser.query.get(c.owner_user_id)
        cv_link = url_for("profileviewer.view", token=s.share_token, _external=True)
        return render_template("profiles/view_public_cv.html", c=c, owner=owner, share=s, cv_link=cv_link)

    pl = RBCVPublicLink.query.filter_by(token=token).first_or_404()
    if pl.status != "active":
        _forbidden("public_link_inactive", token=token, status=pl.status)
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
                    _log_forbidden("public_link_bad_password", token=token, remote_addr=request.remote_addr)
                    return render_template("profiles/view_public_cv.html", c=None, owner=None, share=pl, cv_link=None, need_password=True, error="Invalid password"), 403
            else:
                return render_template("profiles/view_public_cv.html", c=None, owner=None, share=pl, cv_link=None, need_password=True)
    c = _get_cv_profile(pl.cvfile_id)
    owner = RBUser.query.get(c.owner_user_id)
    cv_link = url_for("profileviewer.view", token=pl.token, _external=True)
    return render_template("profiles/view_public_cv.html", c=c, owner=owner, share=pl, cv_link=cv_link, need_password=False)


@profileviewer_bp.get("/file/<token>")
def file(token: str):
    s = RBCVFileShare.query.filter_by(share_token=token).first()
    if s:
        c = _get_cv_profile(s.cvfile_id)
        allow_dl = True
    else:
        pl = RBCVPublicLink.query.filter_by(token=token).first_or_404()
        if pl.status != "active":
            _forbidden("public_link_file_inactive", token=token, status=pl.status)
        if pl.expires_at and pl.expires_at <= datetime.utcnow():
            abort(410)
        c = _get_cv_profile(pl.cvfile_id)
        allow_dl = pl.allow_download

    if not c.pdf_data:
        abort(404)

    download_requested = (request.args.get("download") == "1")
    if download_requested and not allow_dl:
        _forbidden("public_link_download_not_allowed", token=token, cvfile_id=c.cvfile_id)
    as_attachment = download_requested and allow_dl

    return _send_bytes(
        c.pdf_data,
        c.original_filename or "cv.pdf",
        c.mime_type or "application/pdf",
        as_attachment=as_attachment,
    )


@profileviewer_bp.get("/cover/<token>")
def cover(token: str):
    s = RBCVFileShare.query.filter_by(share_token=token).first()
    if s:
        c = _get_cv_profile(s.cvfile_id)
    else:
        pl = RBCVPublicLink.query.filter_by(token=token).first_or_404()
        if pl.status != "active":
            _forbidden("public_link_cover_inactive", token=token, status=pl.status)
        if pl.expires_at and pl.expires_at <= datetime.utcnow():
            abort(410)
        c = _get_cv_profile(pl.cvfile_id)

    if not c.cover_pdf_data:
        abort(404)

    return _send_bytes(
        c.cover_pdf_data,
        c.cover_letter_name or "cover-letter.pdf",
        c.cover_letter_mime or "application/pdf",
        as_attachment=False,
    )


@profileviewer_bp.get("/pair/<token>")
def view_pair(token: str):
    s = RBCVShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        _forbidden("pair_view_not_public", token=token, share_id=s.share_id, owner=s.owner_user_id)

    p = RBCVPair.query.get_or_404(s.cv_id)
    owner = RBUser.query.get(p.user_id)
    return render_template("profiles/view_public_pair.html", pair=p, owner=owner, share=s)


@vcardviewer_bp.get("/<token>")
def view(token: str):
    s = RBVCardShare.query.filter_by(share_token=token).first_or_404()
    if not s.is_public:
        _forbidden("vcard_view_not_public", token=token, share_id=s.share_id, owner=s.owner_user_id)

    v = RBCVProfile.query.get_or_404(s.vcard_id)
    if v.doc_type != "vcard":
        abort(404)
    skills, services = _vcard_items(v.vcard_id)
    owner = RBUser.query.get(v.user_id)
    return render_template("profiles/view_public_vcard.html", vcard=v, skills=skills, services=services, owner=owner, share=s)
