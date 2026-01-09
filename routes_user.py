from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from typing import Optional
from datetime import datetime
import uuid

from extensions import db
from models import RBUser, RBUserProfile, RBAudit, RBModule, RBUserModule, RBFeedback
from modules.chat.models import ChatThread, ChatThreadMember, ChatMessage
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

def _find_admin_user() -> Optional[RBUser]:
    prof = RBUserProfile.query.filter(db.func.lower(RBUserProfile.handle) == "admin").first()
    if prof:
        return RBUser.query.get(prof.user_id)
    admin_email = RBUser.query.filter(db.func.lower(RBUser.email) == "admin").first()
    if admin_email:
        return admin_email
    admin_addr = RBUser.query.filter(RBUser.email.ilike("admin@%")).first()
    if admin_addr:
        return admin_addr
    return RBUser.query.filter_by(is_admin=True).order_by(RBUser.user_id.asc()).first()

def _get_or_create_dm_thread(user_id: int, other_id: int) -> ChatThread:
    dm_threads = (
        db.session.query(ChatThread.thread_id)
        .join(ChatThreadMember, ChatThreadMember.thread_id == ChatThread.thread_id)
        .filter(ChatThreadMember.user_id.in_([user_id, other_id]))
        .filter(ChatThread.thread_type == "dm")
        .group_by(ChatThread.thread_id)
        .having(db.func.count(db.func.distinct(ChatThreadMember.user_id)) == 2)
        .subquery()
    )
    existing = ChatThread.query.filter(
        ChatThread.thread_id.in_(db.session.query(dm_threads.c.thread_id))
    ).first()
    if existing:
        return existing

    thread = ChatThread(thread_type="dm", name=None, created_by=user_id)
    db.session.add(thread)
    db.session.flush()

    now = datetime.utcnow()
    db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=user_id, role="owner", last_read_at=now))
    db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=other_id, role="member", last_read_at=now))
    return thread

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

@user_bp.post("/feedback")
@login_required
def submit_feedback():
    u = current_user.get_user()
    data = request.get_json(silent=True) or {}
    feedback = (data.get("body") or "").strip()
    if not feedback:
        return jsonify({"ok": False, "error": "Feedback required"}), 400

    admin = _find_admin_user()
    if not admin:
        return jsonify({"ok": False, "error": "Admin user not found"}), 500

    thread = _get_or_create_dm_thread(u.user_id, admin.user_id)

    meta = {
        "url": data.get("url"),
        "path": data.get("path"),
        "title": data.get("title"),
        "referrer": data.get("referrer"),
        "userAgent": data.get("userAgent"),
        "platform": data.get("platform"),
        "language": data.get("language"),
        "languages": data.get("languages"),
        "cookieEnabled": data.get("cookieEnabled"),
        "screen": data.get("screen"),
        "viewport": data.get("viewport"),
        "timezone": data.get("timezone"),
        "timestamp": data.get("timestamp"),
    }
    db.session.add(RBFeedback(user_id=u.user_id, body=feedback, meta=meta))

    prof = RBUserProfile.query.get(u.user_id)
    label = (prof.handle if prof and prof.handle else u.email) or f"User {u.user_id}"
    remote_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "-"
    ua_header = request.headers.get("User-Agent", "-")

    def _safe(val):
        return val if val not in (None, "") else "-"

    lines = [
        "Feedback submission",
        f"From: {label} (user_id {u.user_id})",
        f"Page: {_safe(data.get('url'))}",
        f"Title: {_safe(data.get('title'))}",
        f"Feedback: {feedback}",
        "",
        "Client",
        f"User-Agent: {_safe(data.get('userAgent'))}",
        f"Platform: {_safe(data.get('platform'))}",
        f"Language: {_safe(data.get('language'))}",
        f"Languages: {_safe(','.join(data.get('languages') or []))}",
        f"Cookies: {_safe(str(data.get('cookieEnabled')))}",
        f"Screen: {_safe(data.get('screen'))}",
        f"Viewport: {_safe(data.get('viewport'))}",
        f"Timezone: {_safe(data.get('timezone'))}",
        f"Referrer: {_safe(data.get('referrer'))}",
        f"Timestamp: {_safe(data.get('timestamp'))}",
        "",
        "Server",
        f"User-Agent: {ua_header}",
        f"Remote: {remote_ip}",
        f"Path: {_safe(request.path)}",
    ]
    body = "\n".join(lines)

    msg = ChatMessage(thread_id=thread.thread_id, sender_id=u.user_id, body=body)
    db.session.add(msg)
    thread.updated_at = datetime.utcnow()
    mem = ChatThreadMember.query.filter_by(thread_id=thread.thread_id, user_id=u.user_id).first()
    if mem:
        mem.last_read_at = datetime.utcnow()
        db.session.add(mem)
    db.session.commit()

    return jsonify({"ok": True})

@user_bp.get("/feedback/list")
@login_required
def list_feedback():
    u = current_user.get_user()
    scope = (request.args.get("scope") or "").strip().lower()
    is_admin = bool(getattr(u, "is_admin", False))

    q = RBFeedback.query
    if scope == "all" and is_admin:
        pass
    else:
        q = q.filter(RBFeedback.user_id == u.user_id)

    items = q.order_by(RBFeedback.created_at.desc()).limit(25).all()
    user_ids = {f.user_id for f in items}
    profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(user_ids)).all()} if user_ids else {}
    users = {usr.user_id: usr for usr in RBUser.query.filter(RBUser.user_id.in_(user_ids)).all()} if user_ids else {}

    def _label(user_id: int) -> str:
        prof = profiles.get(user_id)
        if prof and prof.handle:
            return prof.handle
        usr = users.get(user_id)
        if usr and usr.email:
            return usr.email
        return f"User {user_id}"

    payload = []
    for f in items:
        meta = f.meta or {}
        payload.append({
            "feedback_id": f.feedback_id,
            "user_id": f.user_id,
            "user_label": _label(f.user_id),
            "body": f.body,
            "created_at": f.created_at.isoformat() if f.created_at else "",
            "page": meta.get("url") or meta.get("path") or "",
            "title": meta.get("title") or "",
        })

    return jsonify({"ok": True, "items": payload})


# Backward compatibility for old /app/welcome path
@user_bp.route("/app/welcome")
def welcome_legacy():
    return redirect(url_for("user.welcome"))
