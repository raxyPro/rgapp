import uuid
from datetime import datetime
from getpass import getpass

from app import create_app
from extensions import db
from models import RBUser, RBUserProfile, RBAudit
from security import hash_password



def create_admin():
    app = create_app()

    with app.app_context():
        print("=== RayGrow Bridge: Create Admin User ===")

        email = input("Admin email: ").strip().lower()
        if not email:
            print("❌ Email is required")
            return

        existing = RBUser.query.filter_by(email=email).first()
        if existing:
            print(f"⚠️ User already exists (id={existing.user_id}, admin={existing.is_admin})")
            return

        while True:
            password = getpass("Admin password: ")
            confirm = getpass("Confirm password: ")
            if password != confirm:
                print("❌ Passwords do not match, try again")
                continue
            if len(password) < 8:
                print("❌ Password must be at least 8 characters")
                continue
            break

        full_name = input("Full name (optional): ").strip()
        display_name = input("Display name (optional): ").strip()

        now = datetime.utcnow()
        event_id = str(uuid.uuid4())

        # --- Create admin user ---
        user = RBUser(
            email=email,
            password_hash=hash_password(password),
            status="active",
            is_admin=True,
            invited_at=now,
            registered_at=now,
            created_at=now,
            updated_at=now
        )
        db.session.add(user)
        db.session.flush()  # get user_id

        # --- Create profile ---
        profile = RBUserProfile(
            user_id=user.user_id,
            rgDisplay=display_name or full_name or email,
            full_name=full_name or None,
            display_name=display_name or None,
            rgData={}
        )
        db.session.add(profile)

        # --- Audit record ---
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
                "email": email,
                "status": "active",
                "is_admin": True
            }
        )
        db.session.add(audit)

        db.session.commit()

        print("\n✅ Admin user created successfully")
        print(f"   User ID : {user.user_id}")
        print(f"   Email   : {user.email}")
        print("   Role    : ADMIN")
        print("   Status  : ACTIVE")


if __name__ == "__main__":
    create_admin()
