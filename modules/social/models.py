from datetime import datetime
from extensions import db


class SocialPost(db.Model):
    __tablename__ = "rb_social_post"

    post_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = db.Column(db.BigInteger, db.ForeignKey("rb_social_post.post_id", ondelete="CASCADE"), nullable=True, index=True)

    body = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(500), nullable=True)
    cvfile_id = db.Column(db.BigInteger, nullable=True, index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    parent = db.relationship("SocialPost", remote_side=[post_id], backref=db.backref("replies", cascade="all, delete-orphan"))

    __table_args__ = (
        db.Index("ix_social_root", "parent_id", "created_at"),
    )


class SocialLike(db.Model):
    __tablename__ = "rb_social_like"

    like_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    post_id = db.Column(db.BigInteger, db.ForeignKey("rb_social_post.post_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("post_id", "user_id", name="uq_social_like"),
    )
