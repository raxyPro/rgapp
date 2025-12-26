# modules/chat/routes.py
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify
from flask_login import login_required

from extensions import db
from models import RBUser
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
    return {u.user_id: u for u in users}

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

    return render_template(
        "chat/index.html",
        threads=threads,
        members_by_thread=members_by_thread,
        users_by_id=users_by_id,
        active_thread=None,
        me_id=me_id,
    )

@chat_bp.get("/new")
@login_required
@module_required("chat")
def new_chat():
    me_id = get_current_user_id()
    users = RBUser.query.filter(RBUser.user_id != me_id).order_by(RBUser.email.asc()).all()
    return render_template("chat/new_chat.html", users=users, me_id=me_id)

@chat_bp.post("/new")
@login_required
@module_required("chat")
def create_chat():
    me_id = get_current_user_id()

    user_ids = request.form.getlist("user_ids")
    user_ids = [int(x) for x in user_ids if str(x).isdigit()]
    user_ids = sorted(list(set(user_ids)))

    if not user_ids:
        abort(400, "Select at least 1 user")

    existing = RBUser.query.filter(RBUser.user_id.in_(user_ids)).all()
    if len(existing) != len(user_ids):
        abort(400, "One or more users not found")

    # DM
    if len(user_ids) == 1:
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

        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner"))
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=other_id, role="member"))
        db.session.commit()

        return redirect(url_for("chat.thread", thread_id=thread.thread_id))

    # Group
    name = (request.form.get("group_name") or "").strip() or "New Group"

    thread = ChatThread(thread_type="group", name=name, created_by=me_id)
    db.session.add(thread)
    db.session.flush()

    db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=me_id, role="owner"))
    for uid in user_ids:
        db.session.add(ChatThreadMember(thread_id=thread.thread_id, user_id=uid, role="member"))

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

    msgs = (
        ChatMessage.query
        .filter_by(thread_id=thread_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(200)
        .all()
    )

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
    )

@chat_bp.post("/t/<int:thread_id>/send")
@login_required
@module_required("chat")
def send_message_http(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)

    body = (request.form.get("body") or "").strip()
    if not body:
        return redirect(url_for("chat.thread", thread_id=thread_id))

    msg = ChatMessage(thread_id=thread_id, sender_id=me_id, body=body)
    db.session.add(msg)

    t = ChatThread.query.get(thread_id)
    if t:
        t.updated_at = datetime.utcnow()

    db.session.commit()
    return redirect(url_for("chat.thread", thread_id=thread_id))

@chat_bp.get("/api/thread/<int:thread_id>/messages")
@login_required
@module_required("chat")
def api_messages(thread_id: int):
    me_id = get_current_user_id()
    require_thread_member(thread_id, me_id)

    msgs = (
        ChatMessage.query
        .filter_by(thread_id=thread_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(200)
        .all()
    )

    return jsonify([
        {
            "message_id": m.message_id,
            "thread_id": m.thread_id,
            "sender_id": m.sender_id,
            "body": m.body,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ])
