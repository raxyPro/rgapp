# modules/chat/models.py
from datetime import datetime
from sqlalchemy import UniqueConstraint, Index
from extensions import db


class ChatThread(db.Model):
    __tablename__ = "rb_chat_thread"

    thread_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # 'dm' or 'group'
    thread_type = db.Column(db.String(10), nullable=False, default="dm")

    # Only used for group chats (optional for dm)
    name = db.Column(db.String(120), nullable=True)

    created_by = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def display_name_for(self, me_user_id: int, members: list["ChatThreadMember"], users_by_id: dict):
        """If group has a name, show it. Else show other user(s) emails."""
        if self.thread_type == "group" and self.name:
            return self.name

        other_ids = [m.user_id for m in members if m.user_id != me_user_id]
        if not other_ids:
            return self.name or "Chat"

        names = []
        for uid in other_ids:
            u = users_by_id.get(uid)
            names.append(getattr(u, "email", f"User {uid}"))
        return ", ".join(names[:3]) + ("…" if len(names) > 3 else "")


class ChatThreadMember(db.Model):
    __tablename__ = "rb_chat_thread_member"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.BigInteger, db.ForeignKey("rb_chat_thread.thread_id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.BigInteger, nullable=False)

    role = db.Column(db.String(20), nullable=False, default="member")  # owner/member
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_chat_thread_member"),
        Index("ix_chat_thread_member_user", "user_id"),
    )


class ChatMessage(db.Model):
    __tablename__ = "rb_chat_message"

    message_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.BigInteger, db.ForeignKey("rb_chat_thread.thread_id", ondelete="CASCADE"), nullable=False)

    sender_id = db.Column(db.BigInteger, nullable=False)
    body = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chat_message_thread_created", "thread_id", "created_at"),
    )
