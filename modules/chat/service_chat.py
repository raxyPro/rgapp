from __future__ import annotations

from sqlalchemy import or_

from extensions import db
from models import RBUser, RBUserProfile
from modules.chat.models import ChatThread, ChatThreadMember, ChatMessage, ChatMessageReaction

# Service layer for chat data access and serialization.

DEFAULT_MSG_LIMIT = 200


def user_label(user: RBUser, profile: RBUserProfile | None = None) -> str:
    """Return a display label without exposing email."""
    # Procedure: user_label.
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


def get_threads_for_user(user_id: int) -> list[ChatThread]:
    # Procedure: get_threads_for_user.
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


def get_members_for_threads(thread_ids: list[int]) -> list[ChatThreadMember]:
    # Procedure: get_members_for_threads.
    if not thread_ids:
        return []
    return ChatThreadMember.query.filter(ChatThreadMember.thread_id.in_(thread_ids)).all()


def get_users_by_ids(user_ids: list[int]) -> dict[int, RBUser]:
    # Procedure: get_users_by_ids.
    if not user_ids:
        return {}
    users = RBUser.query.filter(RBUser.user_id.in_(user_ids)).all()
    profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(user_ids)).all()}
    enriched: dict[int, RBUser] = {}
    for u in users:
        prof = profiles.get(u.user_id)
        label = user_label(u, prof)
        u.display_label = label
        if prof:
            h = (getattr(prof, "handle", "") or "").strip()
            u.handle = h if h and "@" not in h else None
        enriched[u.user_id] = u
    return enriched


def get_message_counts(thread_ids: list[int]) -> dict[int, int]:
    # Procedure: get_message_counts.
    if not thread_ids:
        return {}
    rows = (
        db.session.query(ChatMessage.thread_id, db.func.count(ChatMessage.message_id))
        .filter(ChatMessage.thread_id.in_(thread_ids))
        .group_by(ChatMessage.thread_id)
        .all()
    )
    return {tid: cnt for tid, cnt in rows}


def get_unread_counts(thread_ids: list[int], me_id: int) -> dict[int, int]:
    # Procedure: get_unread_counts.
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


def get_reaction_summaries(message_ids: list[int], me_id: int) -> dict[int, dict]:
    """Return reaction counts and the current user's selection for each message."""
    # Procedure: get_reaction_summaries.
    if not message_ids:
        return {}

    rows = (
        db.session.query(
            ChatMessageReaction.message_id,
            ChatMessageReaction.emoji,
            db.func.count(ChatMessageReaction.reaction_id),
        )
        .filter(ChatMessageReaction.message_id.in_(message_ids))
        .group_by(ChatMessageReaction.message_id, ChatMessageReaction.emoji)
        .all()
    )
    counts: dict[int, dict[str, int]] = {}
    for mid, emoji, cnt in rows:
        counts.setdefault(mid, {})[emoji] = cnt

    my_rows = (
        db.session.query(ChatMessageReaction.message_id, ChatMessageReaction.emoji)
        .filter(ChatMessageReaction.message_id.in_(message_ids))
        .filter(ChatMessageReaction.user_id == me_id)
        .all()
    )
    user_reactions = {mid: emoji for mid, emoji in my_rows}

    return {
        mid: {"counts": counts.get(mid, {}), "user_reaction": user_reactions.get(mid)}
        for mid in message_ids
    }


def serialize_message(m: ChatMessage, reaction_summary: dict | None = None) -> dict:
    # Procedure: serialize_message.
    summary = reaction_summary or {}
    return {
        "message_id": m.message_id,
        "thread_id": m.thread_id,
        "sender_id": m.sender_id,
        "body": m.body,
        "reply_to_message_id": m.reply_to_message_id,
        "created_at": m.created_at.isoformat(),
        "reactions": summary.get("counts", {}),
        "user_reaction": summary.get("user_reaction"),
    }


def get_visible_messages(
    # Procedure: get_visible_messages.
    thread: ChatThread,
    me_id: int,
    since_id: int | None = None,
    limit: int = DEFAULT_MSG_LIMIT,
) -> list[ChatMessage]:
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


def is_member(thread_id: int, user_id: int) -> bool:
    # Procedure: is_member.
    return ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=user_id).first() is not None
