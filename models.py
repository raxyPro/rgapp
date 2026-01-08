#this is change line for test
from datetime import datetime
from sqlalchemy.ext.mutable import MutableDict
from extensions import db


class RBUser(db.Model):
    __tablename__ = "rb_user"

    user_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    email = db.Column(db.String(320), nullable=False, unique=True, index=True)

    password_hash = db.Column(db.String(255), nullable=True)  # NULL/empty until invite accepted + registered
    status = db.Column(
        db.Enum("invited", "active", "blocked", "deleted"),
        nullable=False,
        default="invited",
        index=True,
    )

    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    invited_at = db.Column(db.DateTime, nullable=True)
    invited_by = db.Column(db.BigInteger, nullable=True)

    registered_at = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RBUserProfile(db.Model):
    __tablename__ = "rb_user_profile"

    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id", ondelete="CASCADE"), primary_key=True)

    handle = db.Column(db.String(64), nullable=True, unique=True, index=True)
    rgDisplay = db.Column(db.String(200), nullable=False)  # quick label
    full_name = db.Column(db.String(200), nullable=True)
    display_name = db.Column(db.String(120), nullable=True)

    # keep JSON for later profile fields
    rgData = db.Column(MutableDict.as_mutable(db.JSON), nullable=True)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RBAudit(db.Model):
    __tablename__ = "rb_audit"

    audit_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    event_id = db.Column(db.String(36), nullable=False, index=True)

    tblname = db.Column(db.String(64), nullable=False)
    row_id = db.Column(db.BigInteger, nullable=False)

    audit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    action = db.Column(
        db.Enum("add", "invite", "register", "login", "edit", "grant_module", "revoke_module"),
        nullable=False,
    )

    actor_id = db.Column(db.BigInteger, nullable=True)
    source = db.Column(db.Enum("self", "admin", "api"), nullable=False, default="api")

    prev_data = db.Column(MutableDict.as_mutable(db.JSON), nullable=True)
    new_data = db.Column(MutableDict.as_mutable(db.JSON), nullable=True)


class RBInvitation(db.Model):
    __tablename__ = "rb_invitation"

    invitation_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    email = db.Column(db.String(320), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_invite_email", "email"),
    )


class RBPasswordReset(db.Model):
    __tablename__ = "rb_password_reset"

    reset_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.Index("fk_reset_user", "user_id"),
    )


class RBModule(db.Model):
    __tablename__ = "rb_module"

    # Stable string key so modules are plug-and-play without changing schema.
    module_key = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Global kill-switch (does not override per-user access; both must be enabled).
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RBUserModule(db.Model):
    __tablename__ = "rb_user_module"

    user_id = db.Column(db.BigInteger, db.ForeignKey("rb_user.user_id", ondelete="CASCADE"), primary_key=True)
    module_key = db.Column(db.String(50), db.ForeignKey("rb_module.module_key", ondelete="CASCADE"), primary_key=True)

    has_access = db.Column(db.Boolean, nullable=False, default=True)

    granted_by = db.Column(db.BigInteger, nullable=True)
    granted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "module_key", name="uq_rb_user_module"),
    )

    # Convenience relationships
    user = db.relationship("RBUser", backref=db.backref("module_access", lazy="dynamic", cascade="all, delete-orphan"))
    module = db.relationship("RBModule")
