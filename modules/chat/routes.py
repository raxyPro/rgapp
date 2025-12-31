# modules/chat/routes.py
from __future__ import annotations

from datetime import datetime
import time
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, flash
from flask_login import login_required, current_user
from markupsafe import Markup, escape
import re
from urllib.parse import unquote_plus
from sqlalchemy import or_

from extensions import db
from models import RBUser, RBUserProfile
from modules.chat.models import ChatThread, ChatThreadMember, ChatMessage
from modules.chat.permissions import module_required, require_thread_member
from modules.chat.util import get_current_user_id

chat_bp = Blueprint(
    "chat",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/chat",
)

_URL_RE = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
DEFAULT_MSG_LIMIT = 200


def _user_label(user: RBUser, profile: RBUserProfile | None = None) -> str:
    """Return a display label without exposing email."""
    if profile:
        for candidate in (
            getattr(profile, "handle", None),
            getattr(profile, "rgDisplay", None),
            getattr(profile, "display_name", None),
            getattr(profile, "full_name", None),
        ):
            text = (candidate or "").strip()
            if text and "@" not in text:
                return text
    handle = (getattr(user, "handle", "") or "").strip()
    if handle and "@" not in handle:
        return handle
    return f"User {user.user_id}"


def _visible_messages(thread: ChatThread, me_id: int, since_id: int | None = None, limit: int = DEFAULT_MSG_LIMIT):
    """Return messages visible to this user, applying broadcast visibility rules."""
    q = ChatMessage.query.filter_by(thread_id=thread.thread_id)
    if since_id is not None:
        q = q.filter(ChatMessage.message_id > since_id)

    if thread.thread_type == "broadcast" and me_id != thread.created_by:
        q = q.filter(
            or_(
                ChatMessage.sender_id == thread.created_by,
                ChatMessage.sender_id == me_id,
            )
        )

    return q.order_by(ChatMessage.created_at.asc()).limit(limit).all()


def _render_body_html(body: str) -> Markup:
    """Render message text as safe HTML with links and inline image previews."""
    if not body:
        return Markup("")

    def _replace(match: re.Match) -> str:
        url = match.group(0)
        safe_url = escape(url)
        lower = url.split("?", 1)[0].lower()
        if lower.endswith(_IMAGE_EXTS):
            return (
                f'<a href="{safe_url}" target="_blank" rel="noopener">'
                f'<img src="{safe_url}" alt="Image" style="max-width:240px;max-height:240px;'
                f'border-radius:8px;display:block;margin-top:6px;">'
                f"</a>"
            )
        return f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_url}</a>'

    escaped = escape(body)
    linked = _URL_RE.sub(_replace, escaped)
    html = linked.replace("\n", "<br>")
    return Markup(html)


@chat_bp.app_template_filter("chat_rich")
def chat_rich(body: str) -> Markup:
    return _render_body_html(body)

def _threads_for_user(user_id: int) -> list[ChatThread]:
    thread_ids = (
        db.session.query(ChatThreadMember.thread_id)
        .filter(ChatThreadMember.user_id == user_id)
        .subquery()
    )
    return (
        ChatThread.query
        .filter(ChatThread.thread_id.in_(db.session.query(thread_ids.c.thread_id)))
        .order_by(ChatThread.updated_at.desc())
        .all()
    )

def _members_for_threads(thread_ids: list[int]) -> list[ChatThreadMember]:
    if not thread_ids:
        return []
    return ChatThreadMember.query.filter(ChatThreadMember.thread_id.in_(thread_ids)).all()

def _users_by_ids(user_ids: list[int]) -> dict[int, RBUser]:
    if not user_ids:
        return {}
    users = RBUser.query.filter(RBUser.user_id.in_(user_ids)).all()
    profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(user_ids)).all()}
    enriched = {}
    for u in users:
        prof = profiles.get(u.user_id)
        label = _user_label(u, prof)
        u.display_label = label
        if prof:
            h = (getattr(prof, "handle", "") or "").strip()
            u.handle = h if h and "@" not in h else None
        enriched[u.user_id] = u
    return enriched


def _message_counts(thread_ids: list[int]) -> dict[int, int]:
    if not thread_ids:
        return {}
    rows = (
        db.session.query(ChatMessage.thread_id, db.func.count(ChatMessage.message_id))
        .filter(ChatMessage.thread_id.in_(thread_ids))
        .group_by(ChatMessage.thread_id)
        .all()
    )
    return {tid: cnt for tid, cnt in rows}


def _unread_counts(thread_ids: list[int], me_id: int) -> dict[int, int]:
    if not thread_ids:
        return {}
    rows = (
        db.session.query(ChatMessage.thread_id, db.func.count(ChatMessage.message_id))
        .join(
            ChatThreadMember,
            (ChatThreadMember.thread_id == ChatMessage.thread_id)
            & (ChatThreadMember.user_id == me_id),
        )
        .filter(ChatMessage.thread_id.in_(thread_ids))
        .filter(ChatMessage.sender_id != me_id)
        .filter(
            or_(
                ChatThreadMember.last_read_at.is_(None),
                ChatMessage.created_at > ChatThreadMember.last_read_at,
            )
        )
        .group_by(ChatMessage.thread_id)
        .all()
    )
    return {tid: cnt for tid, cnt in rows}


def _serialize_message(m: ChatMessage) -> dict:
    return {
        "message_id": m.message_id,
        "thread_id": m.thread_id,
        "sender_id": m.sender_id,
        "body": m.body,
        "reply_to_message_id": m.reply_to_message_id,
        "created_at": m.created_at.isoformat(),
    }


POLL_TIMEOUT_SEC = 25
POLL_SLEEP_SEC = 0.1
POLL_MAX_RETURN = 200

@chat_bp.get("/")
@login_required
@module_required("chat")
def index():
    me_id = get_current_user_id()

    threads = _threads_for_user(me_id)
    thread_ids = [t.thread_id for t in threads]
    members = _members_for_threads(thread_ids)
    users_by_id = _users_by_ids(list({m.user_id for m in members}))

    members_by_thread: dict[int, list[ChatThreadMember]] = {}
    for m in members:
        members_by_thread.setdefault(m.thread_id, []).append(m)

    message_counts = _message_counts(thread_ids)
    unread_counts = _unread_counts(thread_ids, me_id)

    return render_template(
        "chat/index.html",
        threads=threads,
        members_by_thread=members_by_thread,
        users_by_id=users_by_id,
        active_thread=None,
        me_id=me_id,
        message_counts=message_counts,
        unread_counts=unread_counts,
    )

@chat_bp.get("/new")
@login_required
@module_required("chat")
def new_chat():
    me_id = get_current_user_id()
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()
    if users:
        ids = [u.user_id for u in users]
        profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(ids)).all()}
        for u in users:
            prof = profiles.get(u.user_id)
            u.display_label = _user_label(u, prof)
    return render_template("chat/new_chat.html", users=users, me_id=me_id)

@chat_bp.post("/new")
@login_required
@module_required("chat")
def create_chat():
    me_id = get_current_user_id()

    chat_type = (request.form.get("chat_type") or "auto").strip().lower()
    user_ids = request.form.getlist("user_ids")
    user_ids = [int(x) for x in user_ids if str(x).isdigit()]
    user_ids = sorted(list(set(user_ids)))

    if not user_ids:
        abort(400, "Select at least 1 user")

    existing = RBUser.query.filter(RBUser.user_id.in_(user_ids)).all()
    if len(existing) != len(user_ids):
        abort(400, "One or more users not found")

    # Broadcast (owner posts; subscribers can reply)
    if chat_type == "broadcast":
        name = (request.form.get("group_name") or "").strip() or "Broadcast"
        thread = ChatThread(thread_type="broadcast", name=name, created_by=me_id)
        db.session.add(thread)
        db.session.flush()

        now = datetime.utcnow()
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner", last_read_at=now))
        for uid in user_ids:
            db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=uid, role="member", last_read_at=now))
        db.session.commit()
        return redirect(url_for("chat.thread", thread_id=thread.thread_id))

    # DM
    if chat_type in ("dm", "auto") and len(user_ids) == 1:
        other_id = user_ids[0]

        dm_threads = (
            db.session.query(ChatThread.thread_id)
            .join(ChatThreadMember, ChatThreadMember.thread_id == ChatThread.thread_id)
            .filter(ChatThreadMember.user_id.in_([me_id, other_id]))
            .filter(ChatThread.thread_type == "dm")
            .group_by(ChatThread.thread_id)
            .having(db.func.count(db.func.distinct(ChatThreadMember.user_id)) == 2)
            .subquery()
        )

        existing_dm = ChatThread.query.filter(
            ChatThread.thread_id.in_(db.session.query(dm_threads.c.thread_id))
        ).first()

        if existing_dm:
            return redirect(url_for("chat.thread", thread_id=existing_dm.thread_id))

        thread = ChatThread(thread_type="dm", name=None, created_by=me_id)
        db.session.add(thread)
        db.session.flush()

        now = datetime.utcnow()
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner", last_read_at=now))
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=other_id, role="member", last_read_at=now))
        db.session.commit()

        return redirect(url_for("chat.thread", thread_id=thread.thread_id))

    # Group
    if chat_type == "group" and len(user_ids) < 2:
        abort(400, "Select at least 2 users for a group")

    name = (request.form.get("group_name") or "").strip() or "New Group"

    thread = ChatThread(thread_type="group", name=name, created_by=me_id)
    db.session.add(thread)
    db.session.flush()

    now = datetime.utcnow()
    db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner", last_read_at=now))
    for uid in user_ids:
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=uid, role="member", last_read_at=now))

    db.session.commit()
    return redirect(url_for("chat.thread", thread_id=thread.thread_id))


@chat_bp.get("/dm_with_note/<int:user_id>")
@login_required
@module_required("chat")
def dm_with_note(user_id: int):
    """Start/open DM with a user and post a prefilled note."""
    me_id = get_current_user_id()
    if user_id == me_id:
        abort(400, "Cannot DM yourself")

    other = RBUser.query.get_or_404(user_id)

    dm_threads = (
        db.session.query(ChatThread.thread_id)
        .join(ChatThreadMember, ChatThreadMember.thread_id == ChatThread.thread_id)
        .filter(ChatThreadMember.user_id.in_([me_id, other.user_id]))
        .filter(ChatThread.thread_type == "dm")
        .group_by(ChatThread.thread_id)
        .having(db.func.count(db.func.distinct(ChatThreadMember.user_id)) == 2)
        .subquery()
    )

    existing_dm = ChatThread.query.filter(
        ChatThread.thread_id.in_(db.session.query(dm_threads.c.thread_id))
    ).first()

    if existing_dm:
        thread = existing_dm
    else:
        thread = ChatThread(thread_type="dm", name=None, created_by=me_id)
        db.session.add(thread)
        db.session.flush()
        now = datetime.utcnow()
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner", last_read_at=now))
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=other.user_id, role="member", last_read_at=now))

    note_raw = request.args.get("note") or ""
    note = unquote_plus(note_raw).strip()
    if not note and note_raw:
        note = note_raw.strip()
    if note:
        msg = ChatMessage(thread_id=thread.thread_id, sender_id=me_id, body=note)
        db.session.add(msg)
        thread.updated_at = datetime.utcnow()

    db.session.commit()
    return redirect(url_for("chat.thread", thread_id=thread.thread_id))


@chat_bp.get("/dm/<int:user_id>")
@login_required
@module_required("chat")
def start_dm(user_id: int):
    """Start or open a DM with the given user."""
    me_id = get_current_user_id()
    if user_id == me_id:
        abort(400, "Cannot DM yourself")

    other = RBUser.query.get_or_404(user_id)

    dm_threads = (
        db.session.query(ChatThread.thread_id)
        .join(ChatThreadMember, ChatThreadMember.thread_id == ChatThread.thread_id)
        .filter(ChatThreadMember.user_id.in_([me_id, other.user_id]))
        .filter(ChatThread.thread_type == "dm")
        .group_by(ChatThread.thread_id)
        .having(db.func.count(db.func.distinct(ChatThreadMember.user_id)) == 2)
        .subquery()
    )

    existing_dm = ChatThread.query.filter(
        ChatThread.thread_id.in_(db.session.query(dm_threads.c.thread_id))
    ).first()

    if existing_dm:
        return redirect(url_for("chat.thread", thread_id=existing_dm.thread_id))

    thread = ChatThread(thread_type="dm", name=None, created_by=me_id)
    db.session.add(thread)
    db.session.flush()

    now = datetime.utcnow()
    db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner", last_read_at=now))
    db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=other.user_id, role="member", last_read_at=now))
    db.session.commit()

    return redirect(url_for("chat.thread", thread_id=thread.thread_id))

@chat_bp.get("/t/<int:thread_id>")
@login_required
@module_required("chat")
def thread(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)

    threads = _threads_for_user(me_id)
    thread_ids = [t.thread_id for t in threads]
    members = _members_for_threads(thread_ids)
    users_by_id = _users_by_ids(list({m.user_id for m in members}))

    members_by_thread: dict[int, list[ChatThreadMember]] = {}
    for m in members:
        members_by_thread.setdefault(m.thread_id, []).append(m)

    t = ChatThread.query.get_or_404(thread_id)

    # Mark as read for the current user.
    my_member = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=me_id).first()
    if my_member:
        my_member.last_read_at = datetime.utcnow()
        db.session.add(my_member)
        db.session.commit()

    message_counts = _message_counts(thread_ids)
    unread_counts = _unread_counts(thread_ids, me_id)

    msgs = _visible_messages(t, me_id)

    manage_members = t.thread_type in ("group", "broadcast") and t.created_by == me_id
    available_users = []
    if manage_members:
        member_ids = {m.user_id for m in members_by_thread.get(thread_id, [])}
        all_users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()
        if all_users:
            ids = [u.user_id for u in all_users]
            profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(ids)).all()}
            for u in all_users:
                prof = profiles.get(u.user_id)
                u.display_label = _user_label(u, prof)
        available_users = [u for u in all_users if u.user_id not in member_ids]

    my_members = members_by_thread.get(thread_id, [])
    display_name = t.display_name_for(me_id, my_members, users_by_id)

    return render_template(
        "chat/thread.html",
        threads=threads,
        members_by_thread=members_by_thread,
        users_by_id=users_by_id,
        active_thread=t,
        active_thread_display_name=display_name,
        messages=msgs,
        me_id=me_id,
        manage_members=manage_members,
        available_users=available_users,
        message_counts=message_counts,
        unread_counts=unread_counts,
    )

@chat_bp.post("/t/<int:thread_id>/send")
@login_required
@module_required("chat")
def send_message_http(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)

    payload = request.get_json(silent=True) if request.is_json else request.form
    reply_to_raw = (payload.get("reply_to_message_id") if payload else None) or (payload.get("reply_to") if payload else None)
    reply_to_id = int(reply_to_raw) if reply_to_raw and str(reply_to_raw).isdigit() else None
    body = ((payload.get("body") if payload else None) or "").strip()
    if not body:
        if request.is_json:
            return jsonify({"ok": False, "error": "Message required"}), 400
        return redirect(url_for("chat.thread", thread_id=thread_id))

    t = ChatThread.query.get_or_404(thread_id)
    is_broadcast = t.thread_type == "broadcast"
    is_owner = t.created_by == me_id

    if is_broadcast and not is_owner:
        if not reply_to_id:
            latest_owner = (
                ChatMessage.query.filter_by(thread_id=thread_id, sender_id=t.created_by)
                .order_by(ChatMessage.message_id.desc())
                .first()
            )
            reply_to_id = latest_owner.message_id if latest_owner else None
        if not reply_to_id:
            if request.is_json:
                return jsonify({"ok": False, "error": "No broadcast message to reply to"}), 400
            flash("You can only reply to existing broadcast messages.", "danger")
            return redirect(url_for("chat.thread", thread_id=thread_id))

    msg = ChatMessage(thread_id=thread_id, sender_id=me_id, body=body, reply_to_message_id=reply_to_id)
    db.session.add(msg)

    t.updated_at = datetime.utcnow()

    my_member = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=me_id).first()
    if my_member:
        my_member.last_read_at = datetime.utcnow()
        db.session.add(my_member)

    db.session.commit()

    if request.is_json:
        return jsonify({"ok": True, "message": _serialize_message(msg)})
    return redirect(url_for("chat.thread", thread_id=thread_id))


@chat_bp.post("/t/<int:thread_id>/m/<int:message_id>/edit")
@login_required
@module_required("chat")
def edit_message(thread_id: int, message_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    msg = ChatMessage.query.get_or_404(message_id)
    me_user = current_user.get_user() if hasattr(current_user, "get_user") else None
    if msg.sender_id != me_id and not (me_user and getattr(me_user, "is_admin", False)):
        abort(403)

    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Message cannot be empty.", "danger")
        return redirect(url_for("chat.thread", thread_id=thread_id))

    msg.body = body
    db.session.add(msg)
    db.session.commit()
    flash("Message updated.", "success")
    return redirect(url_for("chat.thread", thread_id=thread_id))


@chat_bp.post("/t/<int:thread_id>/m/<int:message_id>/delete")
@login_required
@module_required("chat")
def delete_message(thread_id: int, message_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    msg = ChatMessage.query.get_or_404(message_id)

    me_user = current_user.get_user() if hasattr(current_user, "get_user") else None
    if msg.sender_id != me_id and not (me_user and getattr(me_user, "is_admin", False)):
        abort(403)

    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted.", "info")
    return redirect(url_for("chat.thread", thread_id=thread_id))


@chat_bp.post("/t/<int:thread_id>/delete")
@login_required
@module_required("chat")
def delete_thread(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    t = ChatThread.query.get_or_404(thread_id)
    me_user = current_user.get_user() if hasattr(current_user, "get_user") else None
    if not (me_user and getattr(me_user, "is_admin", False)):
        # Allow any member to delete their personal window and messages
        pass

    # Cascades remove members/messages
    db.session.delete(t)
    db.session.commit()
    flash("Chat deleted.", "info")
    return redirect(url_for("chat.index"))


@chat_bp.post("/t/<int:thread_id>/members/add")
@login_required
@module_required("chat")
def add_members(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    thread = ChatThread.query.get_or_404(thread_id)
    if thread.thread_type not in ("group", "broadcast"):
        abort(400, "Cannot add members to this chat type")
    if thread.created_by != me_id:
        abort(403, "Only the owner can add members")

    user_ids = request.form.getlist("user_ids")
    user_ids = [int(x) for x in user_ids if str(x).isdigit()]
    user_ids = sorted(list(set(user_ids)))
    if not user_ids:
        abort(400, "Select at least one user to add")

    existing_ids = {
        m.user_id
        for m in ChatThreadMember.query.filter(ChatThreadMember.thread_id == thread_id).all()
    }
    now = datetime.utcnow()
    added = 0
    for uid in user_ids:
        if uid in existing_ids:
            continue
        db.session.add(ChatThreadMember(thread_id=thread_id, user_id=uid, role="member", last_read_at=now))
        added += 1

    if added:
        db.session.commit()
        flash(f"Added {added} member(s).", "success")
    else:
        flash("No new members added.", "info")
    return redirect(url_for("chat.thread", thread_id=thread_id))


@chat_bp.post("/t/<int:thread_id>/members/<int:user_id>/remove")
@login_required
@module_required("chat")
def remove_member(thread_id: int, user_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    thread = ChatThread.query.get_or_404(thread_id)
    if thread.thread_type not in ("group", "broadcast"):
        abort(400, "Cannot remove members from this chat type")
    if thread.created_by != me_id:
        abort(403, "Only the owner can remove members")
    if user_id == thread.created_by:
        abort(400, "Cannot remove the owner")

    mem = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=user_id).first()
    if mem:
        db.session.delete(mem)
        db.session.commit()
        flash("Member removed.", "info")
    else:
        flash("Member not found.", "warning")
    return redirect(url_for("chat.thread", thread_id=thread_id))

@chat_bp.get("/api/thread/<int:thread_id>/messages")
@login_required
@module_required("chat")
def api_messages(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)

    thread = ChatThread.query.get_or_404(thread_id)
    msgs = _visible_messages(thread, me_id)
    return jsonify([_serialize_message(m) for m in msgs])


@chat_bp.post("/api/thread/<int:thread_id>/send")
@login_required
@module_required("chat")
def api_send(thread_id: int):
    # JSON-only send endpoint for long polling client
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    reply_to_raw = data.get("reply_to_message_id") or data.get("reply_to")
    reply_to_id = int(reply_to_raw) if reply_to_raw and str(reply_to_raw).isdigit() else None
    if not body:
        return jsonify({"ok": False, "error": "Message required"}), 400

    t = ChatThread.query.get_or_404(thread_id)
    is_broadcast = t.thread_type == "broadcast"
    is_owner = t.created_by == me_id

    if is_broadcast and not is_owner:
        if not reply_to_id:
            latest_owner = (
                ChatMessage.query.filter_by(thread_id=thread_id, sender_id=t.created_by)
                .order_by(ChatMessage.message_id.desc())
                .first()
            )
            reply_to_id = latest_owner.message_id if latest_owner else None
        if not reply_to_id:
            return jsonify({"ok": False, "error": "No broadcast message to reply to"}), 400

    msg = ChatMessage(thread_id=thread_id, sender_id=me_id, body=body, reply_to_message_id=reply_to_id)
    db.session.add(msg)

    t.updated_at = datetime.utcnow()

    mem = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=me_id).first()
    if mem:
        mem.last_read_at = datetime.utcnow()
        db.session.add(mem)

    db.session.commit()
    return jsonify({"ok": True, "message": _serialize_message(msg)})


@chat_bp.get("/api/thread/<int:thread_id>/poll")
@login_required
@module_required("chat")
def api_poll(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0

    deadline = time.time() + POLL_TIMEOUT_SEC
    thread = ChatThread.query.get_or_404(thread_id)
    while True:
        new_msgs = (
            _visible_messages(thread, me_id, since_id=since, limit=POLL_MAX_RETURN)
        )
        if new_msgs:
            # touch last_read for requester
            mem = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=me_id).first()
            if mem:
                mem.last_read_at = datetime.utcnow()
                db.session.add(mem)
                db.session.commit()
            return jsonify({"messages": [_serialize_message(m) for m in new_msgs]})

        if time.time() >= deadline:
            return jsonify({"messages": []})

        time.sleep(POLL_SLEEP_SEC)
