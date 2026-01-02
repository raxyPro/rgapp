# modules/chat/models.py
from datetime import datetime
from sqlalchemy import UniqueConstraint, Index
from extensions import db
from sqlalchemy.orm import backref


class ChatThread(db.Model):
    __tablename__ = "rb_chat_thread"

    thread_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # 'dm' or 'group' or 'broadcast'
    thread_type = db.Column(db.Enum("dm", "group", "broadcast"), nullable=False, default="dm")

    # Only used for group/broadcast
    name = db.Column(db.String(120), nullable=True)

    created_by = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_thread_type", "thread_type"),
        Index("ix_chat_thread_updated", "updated_at"),
        Index("fk_chat_thread_created_by", "created_by"),
    )

    def display_name_for(self, me_user_id: int, members: list["ChatThreadMember"], users_by_id: dict):
        """If named (group/broadcast), show name; else show other user handles."""
        if self.thread_type in ("group", "broadcast") and self.name:
            owner = users_by_id.get(self.created_by)
            owner_label = getattr(owner, "display_label", None) or getattr(owner, "handle", None) or f"User {self.created_by}"
            return f"{self.name} by {owner_label}" if self.thread_type == "broadcast" else self.name

        other_ids = [m.user_id for m in members if m.user_id != me_user_id]
        if not other_ids:
            return self.name or "Chat"

        names = []
        for uid in other_ids:
            u = users_by_id.get(uid)
            label = getattr(u, "display_label", None) or getattr(u, "handle", None)
            names.append(label or f"User {uid}")
        return ", ".join(names[:3]) + (" +more" if len(names) > 3 else "")


class ChatThreadMember(db.Model):
    __tablename__ = "rb_chat_thread_member"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.BigInteger, db.ForeignKey("rb_chat_thread.thread_id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id"), nullable=False)

    role = db.Column(db.Enum("owner", "member"), nullable=False, default="member")
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_read_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_chat_thread_member"),
        Index("ix_chat_thread_member_user", "user_id"),
        Index("ix_chat_thread_member_thread", "thread_id"),
    )


class ChatMessage(db.Model):
    __tablename__ = "rb_chat_message"

    message_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.BigInteger, db.ForeignKey("rb_chat_thread.thread_id", ondelete="CASCADE"), nullable=False)

    sender_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    reply_to_message_id = db.Column(db.BigInteger, db.ForeignKey("rb_chat_message.message_id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_message_thread_created", "thread_id", "created_at"),
        Index("ix_chat_msg_sender", "sender_id"),
    )


class ChatMessageReaction(db.Model):
    __tablename__ = "rb_chat_message_reaction"

    reaction_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    message_id = db.Column(
        db.BigInteger,
        db.ForeignKey("rb_chat_message.message_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id"), nullable=False)
    emoji = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    message = db.relationship(
        "ChatMessage",
        backref=backref("reactions", cascade="all, delete-orphan"),
    )

    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_chat_message_reaction"),
        Index("ix_chat_reaction_message", "message_id"),
        Index("ix_chat_reaction_user", "user_id"),
    )
