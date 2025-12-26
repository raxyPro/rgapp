from __future__ import annotations

from datetime import datetime

from extensions import db


class RBCVPair(db.Model):
    __tablename__ = "rb_cv_pair"

    cv_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=False, index=True)

    # vCard fields
    v_name = db.Column(db.String(120), nullable=False, default="")
    v_company = db.Column(db.String(120), nullable=False, default="")
    v_email = db.Column(db.String(120), nullable=False, default="")
    v_phone = db.Column(db.String(50), nullable=False, default="")
    v_primary_skill = db.Column(db.String(120), nullable=False, default="")
    v_skill_description = db.Column(db.Text, nullable=False, default="")
    v_organizations = db.Column(db.String(255), nullable=False, default="")
    v_achievements = db.Column(db.String(255), nullable=False, default="")

    # Generated One-Page CV (HTML)
    onepage_html = db.Column(db.Text, nullable=False, default="")

    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RBCVShare(db.Model):
    __tablename__ = "rb_cv_share"

    share_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    cv_id = db.Column(db.BigInteger, nullable=False, index=True)

    owner_user_id = db.Column(db.BigInteger, nullable=False, index=True)

    # Share targets
    target_user_id = db.Column(db.BigInteger, nullable=True, index=True)
    target_email = db.Column(db.String(200), nullable=True, index=True)

    # Public viewing
    share_token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    is_public = db.Column(db.Boolean, nullable=False, default=False)

    # Archive the share in "Shared with me"
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
