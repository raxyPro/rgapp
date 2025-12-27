from __future__ import annotations

from datetime import datetime
from extensions import db


class RBVCard(db.Model):
    __tablename__ = "rb_vcard"

    vcard_id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False, unique=True, index=True)

    name = db.Column(db.String(150), nullable=False, default="")
    email = db.Column(db.String(150), nullable=False, default="")
    phone = db.Column(db.String(60), nullable=False, default="")
    linkedin_url = db.Column(db.String(255), nullable=False, default="")
    tagline = db.Column(db.String(255), nullable=False, default="")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

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
