from datetime import datetime
from extensions import db

class RBUser(db.Model):
    __tablename__ = "rb_user"

    user_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    email = db.Column(db.String(320), nullable=False, unique=True, index=True)

    password_hash = db.Column(db.String(255), nullable=True)  # NULL until invite accepted + registered
    status = db.Column(db.Enum("invited", "active", "blocked", "deleted"), nullable=False, default="invited", index=True)

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

    rgDisplay = db.Column(db.String(200), nullable=False)  # quick label
    full_name = db.Column(db.String(200), nullable=True)
    display_name = db.Column(db.String(120), nullable=True)

    # keep JSON for later profile fields
    rgData = db.Column(db.JSON, nullable=True)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class RBAudit(db.Model):
    __tablename__ = "rb_audit"

    audit_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    event_id = db.Column(db.String(36), nullable=False, index=True)

    tblname = db.Column(db.String(64), nullable=False)
    row_id = db.Column(db.BigInteger, nullable=False)

    audit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    action = db.Column(db.Enum("add", "invite", "register", "login", "edit"), nullable=False)

    actor_id = db.Column(db.BigInteger, nullable=True)
    source = db.Column(db.Enum("self", "admin", "api"), nullable=False, default="api")

    prev_data = db.Column(db.JSON, nullable=True)
    new_data = db.Column(db.JSON, nullable=True)
