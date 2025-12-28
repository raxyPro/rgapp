from flask import abort
from flask_login import current_user
from flask_socketio import emit, join_room

from extensions import db, socketio
from modules.chat.models import ChatMessage, ChatThread, ChatThreadMember
from modules.chat.permissions import require_thread_member, module_required
from modules.chat.util import get_current_user_id
from models import RBModule, RBUserModule


def _ensure_chat_access(user_id: int):
    """Validate chat module access and membership."""
    has = (
        db.session.query(RBUserModule)
        .join(RBModule, RBModule.module_key == RBUserModule.module_key)
        .filter(
            RBUserModule.user_id == user_id,
            RBUserModule.module_key == "chat",
            RBUserModule.has_access.is_(True),
            RBModule.is_enabled.is_(True),
        )
        .first()
    )
    if not has:
        abort(403)


def register_chat_sockets(app):
    @socketio.on("chat:join")
    def handle_join(data):
        user_id = get_current_user_id()
        thread_id = int(data.get("thread_id"))
        _ensure_chat_access(user_id)
        require_thread_member(thread_id, user_id)
        join_room(f"thread:{thread_id}")
        emit("chat:joined", {"thread_id": thread_id})

    @socketio.on("chat:send")
    def handle_send(data):
        user_id = get_current_user_id()
        thread_id = int(data.get("thread_id"))
        body = (data.get("body") or "").strip()
        if not body:
            return

        _ensure_chat_access(user_id)
        require_thread_member(thread_id, user_id)

        msg = ChatMessage(thread_id=thread_id, sender_id=user_id, body=body)
        db.session.add(msg)

        t = ChatThread.query.get(thread_id)
        if t:
            t.updated_at = db.func.now()

        # Sender has read up to now; update last_read_at.
        mem = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=user_id).first()
        if mem:
            mem.last_read_at = db.func.now()
            db.session.add(mem)

        db.session.commit()

        emit(
            "chat:new_message",
            {
                "message_id": msg.message_id,
                "thread_id": thread_id,
                "sender_id": user_id,
                "body": body,
                "created_at": msg.created_at.isoformat(),
            },
            room=f"thread:{thread_id}",
        )
