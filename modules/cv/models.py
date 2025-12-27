from __future__ import annotations

from datetime import datetime
from extensions import db


class RBVCard(db.Model):
    __tablename__ = "rb_vcard"

    vcard_id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False, unique=True)

    name = db.Column(db.String(150), nullable=False, default="")
    email = db.Column(db.String(150), nullable=False, default="")
    phone = db.Column(db.String(60), nullable=False, default="")
    linkedin_url = db.Column(db.String(255), nullable=False, default="")
    tagline = db.Column(db.String(255), nullable=False, default="")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_rb_vcard_user"),
        db.Index("idx_rb_vcard_user", "user_id"),
    )

    def touch(self):
        self.updated_at = datetime.utcnow()


class RBVCardItem(db.Model):
    __tablename__ = "rb_vcard_item"

    item_id = db.Column(db.BigInteger, primary_key=True)
    vcard_id = db.Column(db.BigInteger, nullable=False, index=True)

    # 'skill' or 'service'
    item_type = db.Column(db.String(20), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    experience = db.Column(db.Text, nullable=False, default="")  # free text (NOT years)

    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_rb_vcard_item_vcard", "vcard_id"),
        db.Index("idx_rb_vcard_item_type", "item_type"),
    )


class RBCVFile(db.Model):
    __tablename__ = "rb_cv_file"

    cvfile_id = db.Column(db.BigInteger, primary_key=True)
    owner_user_id = db.Column(db.BigInteger, nullable=False, index=True)

    cv_name = db.Column(db.String(200), nullable=False, default="")

    original_filename = db.Column(db.String(255), nullable=False, default="")
    stored_path = db.Column(db.String(500), nullable=False, default="")
    mime_type = db.Column(db.String(100), nullable=False, default="application/pdf")
    size_bytes = db.Column(db.BigInteger, nullable=False, default=0)

    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def touch(self):
        self.updated_at = datetime.utcnow()

    __table_args__ = (
        db.Index("idx_rb_cv_file_owner", "owner_user_id"),
        db.Index("idx_rb_cv_file_arch", "is_archived"),
    )


class RBVCardShare(db.Model):
    __tablename__ = "rb_vcard_share"

    share_id = db.Column(db.BigInteger, primary_key=True)
    vcard_id = db.Column(db.BigInteger, nullable=False, index=True)
    owner_user_id = db.Column(db.BigInteger, nullable=False, index=True)

    target_user_id = db.Column(db.BigInteger, nullable=True, index=True)
    target_email = db.Column(db.String(200), nullable=True, index=True)

    share_token = db.Column(db.String(64), nullable=False, unique=True)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("share_token", name="uq_rb_vcard_share_token"),
        db.Index("idx_rb_vcard_share_vcard", "vcard_id"),
        db.Index("idx_rb_vcard_share_owner", "owner_user_id"),
        db.Index("idx_rb_vcard_share_target_user", "target_user_id"),
        db.Index("idx_rb_vcard_share_target_email", "target_email"),
    )


class RBCVFileShare(db.Model):
    __tablename__ = "rb_cvfile_share"

    share_id = db.Column(db.BigInteger, primary_key=True)
    cvfile_id = db.Column(db.BigInteger, nullable=False, index=True)
    owner_user_id = db.Column(db.BigInteger, nullable=False, index=True)

    target_user_id = db.Column(db.BigInteger, nullable=True, index=True)
    target_email = db.Column(db.String(200), nullable=True, index=True)

    share_token = db.Column(db.String(64), nullable=False, unique=True)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("share_token", name="uq_rb_cvfile_share_token"),
        db.Index("idx_rb_cvfile_share_cvfile", "cvfile_id"),
        db.Index("idx_rb_cvfile_share_owner", "owner_user_id"),
        db.Index("idx_rb_cvfile_share_target_user", "target_user_id"),
        db.Index("idx_rb_cvfile_share_target_email", "target_email"),
    )


class RBCVPair(db.Model):
    __tablename__ = "rb_cv_pair"

    cv_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=False)

    v_name = db.Column(db.String(120), nullable=False, default="")
    v_company = db.Column(db.String(120), nullable=False, default="")
    v_email = db.Column(db.String(120), nullable=False, default="")
    v_phone = db.Column(db.String(50), nullable=False, default="")
    v_primary_skill = db.Column(db.String(120), nullable=False, default="")
    v_skill_description = db.Column(db.Text, nullable=False, default="")
    v_organizations = db.Column(db.String(255), nullable=False, default="")
    v_achievements = db.Column(db.String(255), nullable=False, default="")

    op_name = db.Column(db.String(120), nullable=False, default="")
    op_email = db.Column(db.String(120), nullable=False, default="")
    op_phone = db.Column(db.String(50), nullable=False, default="")
    op_title = db.Column(db.String(150), nullable=False, default="")
    op_linkedin_url = db.Column(db.String(255), nullable=False, default="")
    op_website_url = db.Column(db.String(255), nullable=False, default="")
    op_about = db.Column(db.Text, nullable=False, default="")
    op_skills = db.Column(db.Text, nullable=False, default="")
    op_experience = db.Column(db.Text, nullable=False, default="")
    op_academic = db.Column(db.Text, nullable=False, default="")
    op_achievements = db.Column(db.Text, nullable=False, default="")
    op_final_remark = db.Column(db.Text, nullable=False, default="")

    onepage_html = db.Column(db.Text, nullable=False, default="")

    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_cv_user", "user_id"),
    )


class RBCVShare(db.Model):
    __tablename__ = "rb_cv_share"

    share_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    cv_id = db.Column(db.BigInteger, nullable=False)
    owner_user_id = db.Column(db.BigInteger, nullable=False)

    target_user_id = db.Column(db.BigInteger, nullable=True)
    target_email = db.Column(db.String(200), nullable=True)

    share_token = db.Column(db.String(64), nullable=False)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("share_token", name="uk_share_token"),
        db.Index("idx_share_cv", "cv_id"),
        db.Index("idx_share_owner", "owner_user_id"),
        db.Index("idx_share_target_user", "target_user_id"),
        db.Index("idx_share_target_email", "target_email"),
    )
