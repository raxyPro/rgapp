import uuid
from datetime import datetime

from app import create_app
from extensions import db
from models import RBUser, RBUserProfile, RBAudit, RBModule, RBUserModule
from security import hash_password

# =========================
# EDIT THESE VALUES
# =========================
ADMIN_EMAIL = "ramu@rcpro.in"
ADMIN_PASSWORD = "admin123"       # must be >= 8 chars
ADMIN_FULL_NAME = "Rampal Admin"
ADMIN_DISPLAY_NAME = "Admin"

# Deletion mode:
# - "by_email": delete admin with ADMIN_EMAIL only
# - "all_admins": delete ALL users where is_admin=1
DELETE_MODE = "by_email"
# =========================


def delete_existing_admins():
    """
    Deletes existing admin user(s) depending on DELETE_MODE.
    Also deletes related profile and audit rows for cleanliness.
    """
    if DELETE_MODE == "all_admins":
        admins = RBUser.query.filter_by(is_admin=True).all()
    else:
        # by_email
        admins = RBUser.query.filter_by(email=ADMIN_EMAIL.lower()).all()

    if not admins:
        print("No existing admin user found to delete.")
        return

    for u in admins:
        print(f"Deleting existing user_id={u.user_id}, email={u.email}, is_admin={u.is_admin}")

        # Delete profile first (FK cascade might do this, but safe either way)
        RBUserProfile.query.filter_by(user_id=u.user_id).delete()

        # Delete audits for that user row (optional; keeps DB tidy for dev)
        RBAudit.query.filter_by(tblname="rb_user", row_id=u.user_id).delete()
        RBAudit.query.filter_by(tblname="rb_user_profile", row_id=u.user_id).delete()

        # Delete user
        db.session.delete(u)

    db.session.flush()


def create_admin_always():
    app = create_app()
    with app.app_context():
        print("===============================================")
        print("⚠️  WARNING: This script will DELETE existing")
        print("   admin user(s) and CREATE a NEW admin user.")
        print("===============================================")
        print(f"Delete mode : {DELETE_MODE}")
        print(f"Admin email : {ADMIN_EMAIL}")
        print("Running...\n")

        if not ADMIN_EMAIL or "@" not in ADMIN_EMAIL:
            raise ValueError("ADMIN_EMAIL must be set to a valid email address")
        if not ADMIN_PASSWORD or len(ADMIN_PASSWORD) < 8:
            raise ValueError("ADMIN_PASSWORD must be at least 8 characters")

        now = datetime.utcnow()
        event_id = str(uuid.uuid4())

        try:
            # Start a clean transaction
            delete_existing_admins()

            # Create fresh admin user
            pw = ADMIN_PASSWORD
            print("ADMIN_PASSWORD chars =", len(pw))
            print("ADMIN_PASSWORD bytes =", len(pw.encode("utf-8")))
            print("ADMIN_PASSWORD repr  =", repr(pw))

            user = RBUser(
                email=ADMIN_EMAIL.strip().lower(),
                password_hash=hash_password(pw),
                status="active",
                is_admin=True,
                invited_at=now,
                registered_at=now,
                created_at=now,
                updated_at=now
            )
            db.session.add(user)
            db.session.flush()  # gets user_id

            # Create/attach profile
            profile = RBUserProfile(
                user_id=user.user_id,
                rgDisplay=ADMIN_DISPLAY_NAME or ADMIN_FULL_NAME or ADMIN_EMAIL,
                full_name=ADMIN_FULL_NAME or None,
                display_name=ADMIN_DISPLAY_NAME or None,
                rgData={}
            )
            db.session.add(profile)

            # Audit record
            audit = RBAudit(
                event_id=event_id,
                tblname="rb_user",
                row_id=user.user_id,
                audit_date=now,
                action="add",
                actor_id=user.user_id,
                source="admin",
                prev_data=None,
                new_data={
                    "email": user.email,
                    "status": user.status,
                    "is_admin": True
                }
            )
            db.session.add(audit)

            # Grant social by default if enabled
            social_mod = RBModule.query.filter_by(module_key="social", is_enabled=True).first()
            if social_mod:
                db.session.add(RBUserModule(user_id=user.user_id, module_key="social", has_access=True, granted_by=user.user_id))

            db.session.commit()

            print("✅ Admin user recreated successfully")
            print(f"   User ID : {user.user_id}")
            print(f"   Email   : {user.email}")
            print("   Role    : ADMIN")
            print("   Status  : ACTIVE")

        except Exception as e:
            db.session.rollback()
            print("❌ Failed to recreate admin user.")
            raise


if __name__ == "__main__":
    create_admin_always()
