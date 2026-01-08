from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import synonym

from extensions import db


class RBCVProfile(db.Model):
    """
    Unified CV + vCard record.
    - doc_type: 'vcard' or 'cv'
    - details: JSON payload; for vcards it stores fields like name/email/phone/etc + skills/services arrays.
               for CVs it stores cv_name, cover_letter, job_pref, original_filename, cover_letter_* metadata.
    - pdf_data: binary CV (for doc_type='cv'); leave null for vCards.
    """

    __tablename__ = "rb_cv_profile"

    vcard_id = db.Column("profile_id", db.BigInteger, primary_key=True, autoincrement=True)
    cvfile_id = synonym("vcard_id")

    user_id = db.Column(db.BigInteger, nullable=False, index=True)
    owner_user_id = synonym("user_id")

    doc_type = db.Column(db.String(20), nullable=False, index=True)  # 'vcard' or 'cv'
    details = db.Column(MutableDict.as_mutable(db.JSON), nullable=False, default=dict)

    pdf_data = db.Column(db.LargeBinary, nullable=True)
    pdf_name = db.Column(db.String(255), nullable=True)
    pdf_mime = db.Column(db.String(120), nullable=True)
    pdf_size = db.Column(db.BigInteger, nullable=True)

    cover_pdf_data = db.Column(db.LargeBinary, nullable=True)
    cover_pdf_name = db.Column(db.String(255), nullable=True)
    cover_pdf_mime = db.Column(db.String(120), nullable=True)
    cover_pdf_size = db.Column(db.BigInteger, nullable=True)

    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_cv_profile_user_type", "user_id", "doc_type"),
        db.Index("idx_cv_profile_user", "user_id"),
    )

    # --- helpers ---
    def touch(self):
        self.updated_at = datetime.utcnow()

    def _details(self) -> Dict[str, Any]:
        if self.details is None:
            self.details = {}
        return self.details

    def _set_detail(self, key: str, value: Any):
        data = self._details()
        data[key] = value
        self.details = data

    # vCard-like fields
    @property
    def name(self) -> str:
        return (self._details().get("name") or "").strip()

    @name.setter
    def name(self, val: str):
        self._set_detail("name", (val or "").strip())

    @property
    def email(self) -> str:
        return (self._details().get("email") or "").strip()

    @email.setter
    def email(self, val: str):
        self._set_detail("email", (val or "").strip())

    @property
    def phone(self) -> str:
        return (self._details().get("phone") or "").strip()

    @phone.setter
    def phone(self, val: str):
        self._set_detail("phone", (val or "").strip())

    @property
    def linkedin_url(self) -> str:
        return (self._details().get("linkedin_url") or "").strip()

    @linkedin_url.setter
    def linkedin_url(self, val: str):
        self._set_detail("linkedin_url", (val or "").strip())

    @property
    def tagline(self) -> str:
        return (self._details().get("tagline") or "").strip()

    @tagline.setter
    def tagline(self, val: str):
        self._set_detail("tagline", (val or "").strip())

    @property
    def location(self) -> Optional[str]:
        return (self._details().get("location") or None) or None

    @location.setter
    def location(self, val: Optional[str]):
        self._set_detail("location", (val or "").strip() or None)

    @property
    def work_mode(self) -> Optional[str]:
        return (self._details().get("work_mode") or None) or None

    @work_mode.setter
    def work_mode(self, val: Optional[str]):
        self._set_detail("work_mode", (val or "").strip() or None)

    @property
    def city(self) -> Optional[str]:
        return (self._details().get("city") or None) or None

    @city.setter
    def city(self, val: Optional[str]):
        self._set_detail("city", (val or "").strip() or None)

    @property
    def available_from(self) -> Optional[str]:
        return self._details().get("available_from") or None

    @available_from.setter
    def available_from(self, val: Optional[str]):
        self._set_detail("available_from", val or None)

    @property
    def hours_per_day(self) -> Optional[int]:
        hrs = self._details().get("hours_per_day")
        return int(hrs) if hrs not in (None, "") else None

    @hours_per_day.setter
    def hours_per_day(self, val: Optional[int]):
        self._set_detail("hours_per_day", val if val is not None else None)

    @property
    def skills(self) -> List[Dict[str, Any]]:
        return self._details().get("skills") or []

    @skills.setter
    def skills(self, val: List[Dict[str, Any]]):
        self._set_detail("skills", val or [])

    @property
    def services(self) -> List[Dict[str, Any]]:
        return self._details().get("services") or []

    @services.setter
    def services(self, val: List[Dict[str, Any]]):
        self._set_detail("services", val or [])

    # CV-like fields
    @property
    def cv_name(self) -> str:
        return (self._details().get("cv_name") or "").strip()

    @cv_name.setter
    def cv_name(self, val: str):
        self._set_detail("cv_name", (val or "").strip())

    @property
    def cover_letter(self) -> Optional[str]:
        return self._details().get("cover_letter")

    @cover_letter.setter
    def cover_letter(self, val: Optional[str]):
        self._set_detail("cover_letter", (val or None))

    @property
    def job_pref(self) -> Optional[str]:
        return self._details().get("job_pref")

    @job_pref.setter
    def job_pref(self, val: Optional[str]):
        self._set_detail("job_pref", (val or None))

    @property
    def original_filename(self) -> str:
        return (self._details().get("original_filename") or self.pdf_name or "").strip()

    @original_filename.setter
    def original_filename(self, val: str):
        self._set_detail("original_filename", (val or "").strip())

    @property
    def cover_letter_name(self) -> Optional[str]:
        return self._details().get("cover_letter_name")

    @cover_letter_name.setter
    def cover_letter_name(self, val: Optional[str]):
        self._set_detail("cover_letter_name", val or None)

    @property
    def cover_letter_mime(self) -> Optional[str]:
        return self._details().get("cover_letter_mime")

    @cover_letter_mime.setter
    def cover_letter_mime(self, val: Optional[str]):
        self._set_detail("cover_letter_mime", val or None)

    @property
    def cover_letter_size(self) -> Optional[int]:
        size = self._details().get("cover_letter_size")
        return int(size) if size not in (None, "") else None

    @cover_letter_size.setter
    def cover_letter_size(self, val: Optional[int]):
        self._set_detail("cover_letter_size", val if val is not None else None)

    @property
    def mime_type(self) -> Optional[str]:
        return self.pdf_mime

    @mime_type.setter
    def mime_type(self, val: Optional[str]):
        self.pdf_mime = val

    @property
    def size_bytes(self) -> Optional[int]:
        return self.pdf_size

    @size_bytes.setter
    def size_bytes(self, val: Optional[int]):
        self.pdf_size = val


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


class RBCVPublicLink(db.Model):
    __tablename__ = "rb_cv_public_link"

    link_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    cvfile_id = db.Column(
        db.BigInteger,
        db.ForeignKey("rb_cv_profile.profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = db.Column(db.BigInteger, nullable=False, index=True)
    share_type = db.Column(db.Enum("public", "user", "email"), nullable=False, default="public")
    target = db.Column(db.String(320), nullable=True)

    name = db.Column(db.String(150), nullable=True)
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    allow_download = db.Column(db.Boolean, nullable=False, default=False)

    password_hash = db.Column(db.String(255), nullable=True)

    status = db.Column(db.Enum("active", "disabled"), nullable=False, default="active")
    expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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
