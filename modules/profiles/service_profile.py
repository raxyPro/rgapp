from __future__ import annotations

import json
from datetime import datetime
import uuid
from pathlib import Path

from flask import abort, current_app, request
from flask_login import current_user

from extensions import db
from models import RBUser, RBUserProfile
from modules.chat.util import get_current_user_id
from modules.profiles.models import RBCVPair, RBCVProfile
from models import RBAudit

# Service layer for profile business logic and data access.


def _current_user_email_lower() -> str:
    me = current_user.get_user() if hasattr(current_user, "get_user") else None
    return (getattr(me, "email", "") or "").strip().lower()


def _log_event(kind: str, reason: str, **context) -> None:
    """Append a structured event to the Profiles log file."""
    try:
        cfg_path = current_app.config.get("CV_FORBIDDEN_LOG") if current_app else None
        log_path = Path(cfg_path) if cfg_path else Path(__file__).resolve().parent / "profiles_forbidden.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "kind": kind,
            "reason": reason,
            "path": request.path,
            "method": request.method,
            "user_id": get_current_user_id(),
            "email": _current_user_email_lower(),
            "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
            "context": context,
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        # Never block the request because of logging issues
        pass


def _forbidden(reason: str, **context):
    _log_event("forbidden", reason, **context)
    abort(403)


def _log_access(reason: str, **context):
    """Log a successful access event (helps validate logging pipeline)."""
    _log_event("ok", reason, **context)


def _get_or_create_vcard(user_id: int) -> RBCVProfile:
    v = RBCVProfile.query.filter_by(user_id=user_id, doc_type="vcard").first()
    if not v:
        v = RBCVProfile(
            user_id=user_id,
            doc_type="vcard",
            details={
                "name": "",
                "email": "",
                "phone": "",
                "linkedin_url": "",
                "tagline": "",
                "location": None,
                "work_mode": None,
                "city": None,
                "available_from": None,
                "hours_per_day": None,
                "job_pref_loc": None,
                "job_pref_mode": None,
                "job_pref_city": None,
                "job_pref_hours": None,
                "skills": [],
                "services": [],
            },
        )
        db.session.add(v)
        db.session.flush()
        db.session.add(
            RBAudit(
                event_id=str(uuid.uuid4()),
                tblname="rb_cv_profile",
                row_id=v.vcard_id,
                doc_type="vcard",
                action="add",
                actor_id=get_current_user_id(),
                source="self",
                prev_data=None,
                new_data=v.details,
            )
        )
        db.session.commit()
    return v


def _job_pref_from_vcard(v: RBCVProfile) -> str:
    parts = []
    loc = v.job_pref_loc or v.location
    mode = v.job_pref_mode or v.work_mode
    city = v.job_pref_city or v.city
    hours = v.job_pref_hours or v.hours_per_day
    if loc:
        parts.append(f"Location: {loc}")
    if mode:
        label = "Work from office" if mode == "wfo" else ("Hybrid" if mode == "hybrid" else "Remote")
        parts.append(f"Mode: {label}")
    if city:
        parts.append(f"City: {city}")
    if v.available_from:
        parts.append(f"Available from: {v.available_from}")
    if hours:
        parts.append(f"Hours/day: {hours}")
    return "; ".join(parts)


def _job_pref_from_fields(loc: str | None, mode: str | None, city: str | None, hours: str | None) -> str:
    parts = []
    if loc:
        parts.append(f"Location: {loc}")
    if mode:
        label = "Work from office" if mode == "wfo" else ("Hybrid" if mode == "hybrid" else "Remote")
        parts.append(f"Mode: {label}")
    if city:
        parts.append(f"City: {city}")
    if hours:
        parts.append(f"Hours/day: {hours}")
    return "; ".join(parts)


def _vcard_items(vcard_id: int):
    vcard = RBCVProfile.query.filter_by(vcard_id=vcard_id, doc_type="vcard").first()
    if not vcard:
        return [], []
    skills = sorted(vcard.skills or [], key=lambda i: i.get("sort_order", 0))
    services = sorted(vcard.services or [], key=lambda i: i.get("sort_order", 0))
    return skills, services


def _get_cv_profile(cvfile_id: int) -> RBCVProfile:
    c = RBCVProfile.query.get_or_404(cvfile_id)
    if c.doc_type != "cv":
        abort(404)
    return c


def _find_user_by_handle(handle: str) -> RBUser | None:
    if not handle:
        return None
    h = handle.strip().lower()
    prof = RBUserProfile.query.filter(RBUserProfile.handle == h).first()
    if prof:
        return RBUser.query.get(prof.user_id)
    return None


def _cv_name_exists(user_id: int, name: str, exclude_id: int | None = None) -> bool:
    q = RBCVProfile.query.filter_by(user_id=user_id, doc_type="cv", is_archived=False)
    if exclude_id:
        q = q.filter(RBCVProfile.cvfile_id != exclude_id)
    for cv in q.all():
        if cv.cv_name.lower() == name.lower():
            return True
    return False


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


def build_vcard_export(vcard: RBCVProfile) -> dict:
    """Return a JSON-serializable export payload for a vCard."""
    skills, services = _vcard_items(vcard.vcard_id)
    return {
        "user_id": vcard.user_id,
        "doc_type": vcard.doc_type,
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
        "skills": skills,
        "services": services,
    }


def log_profile_action(action: str, status: str, **context) -> None:
    """Append a structured profile action event to a module-local log."""
    try:
        cfg_path = current_app.config.get("PROFILES_ACTION_LOG") if current_app else None
        log_path = Path(cfg_path) if cfg_path else Path(__file__).resolve().parent / "profiles.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "status": status,
            "path": request.path,
            "method": request.method,
            "user_id": get_current_user_id(),
            "email": _current_user_email_lower(),
            "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
            "context": context,
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        # Never block the request because of logging issues
        pass
