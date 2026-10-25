"""Development database seed script for SIH Training Centre AI Monitoring.

*** LOCAL DEVELOPMENT UTILITY ONLY — NEVER USE IN PRODUCTION ***

Usage:
    python -m backend.app.seed [--email EMAIL] [--password PASSWORD] [--name NAME]
Or via environment variables:
    DEV_ADMIN_EMAIL=admin@sih.gov.in DEV_ADMIN_PASSWORD=your_password python -m backend.app.seed
"""

import sys
import os
import argparse
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

try:
    from backend.app.core.database import SessionLocal
    from backend.app.core.security import get_password_hash
    from backend.app.models.user import User
except ImportError:
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    from app.models.user import User


def seed_admin(email: str, password: str, name: str = "System Administrator") -> bool:
    print("\n=======================================================")
    print("  SIH MONITORING - DEVELOPMENT SEED UTILITY")
    print("  WARNING: Local development only. Do not use in production.")
    print("=======================================================\n")

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"[INFO] User with email '{email}' already exists (Role: {existing.role}). No changes made.")
            return True

        pw_hash = get_password_hash(password)
        admin_user = User(
            name=name,
            email=email,
            password_hash=pw_hash,
            role="ADMIN",
            centre_id=None,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"[SUCCESS] Created development admin account:")
        print(f"  - ID:    {admin_user.id}")
        print(f"  - Name:  {admin_user.name}")
        print(f"  - Email: {admin_user.email}")
        print(f"  - Role:  {admin_user.role}")
        print("\nPassword has been securely hashed using bcrypt.")
        return True
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to seed development user: {exc}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed initial development admin user")
    parser.add_argument(
        "--email",
        default=os.getenv("DEV_ADMIN_EMAIL", "admin@sih.gov.in"),
        help="Admin email address",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("DEV_ADMIN_PASSWORD", "AdminPassword123!"),
        help="Admin password (will be hashed with bcrypt)",
    )
    parser.add_argument(
        "--name",
        default=os.getenv("DEV_ADMIN_NAME", "System Administrator"),
        help="Admin full name",
    )

    args = parser.parse_args()
    seed_admin(email=args.email, password=args.password, name=args.name)


if __name__ == "__main__":
    main()
