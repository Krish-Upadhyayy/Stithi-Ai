#!/usr/bin/env python3
"""scripts/seed_demo.py — Controlled Demo Data Seeding Script for SIH Presentation.

*** STANDALONE DEMO SEEDER ONLY — NEVER RUNS AUTOMATICALLY ***
*** ALL CREATED ENTITIES ARE EXPLICITLY LABELED [DEMO] ***

Usage:
    # Dry run / Help:
    python scripts/seed_demo.py

    # Execute seed:
    python scripts/seed_demo.py --execute

    # Clean / Remove demo entities:
    python scripts/seed_demo.py --clean
"""

import sys
import os
import argparse
from datetime import date, datetime
import cv2
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.camera import Camera
from backend.app.models.inventory import InventoryItem
from backend.app.models.session import MonitoringSession

DEMO_CENTRE_CODE = "DEMO-TC-001"
DEMO_CENTRE_NAME = "[DEMO] National Skilling Centre Delhi-01"
DEMO_ADMIN_EMAIL = "demo_admin@sih.gov.in"
DEMO_ADMIN_PASS = "DemoAdmin123!"
DEMO_VIDEO_PATH = "data/input/demo_classroom_sample.mp4"


def generate_sample_demo_video(output_path: str, duration_sec: int = 5, fps: int = 10) -> str:
    """Creates a local, lightweight demo MP4 clip if none exists."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path

    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_sec * fps
    for frame_idx in range(total_frames):
        # Create a clean classroom layout frame
        img = np.full((height, width, 3), 35, dtype=np.uint8)

        # Draw a simulated whiteboard
        cv2.rectangle(img, (120, 30), (520, 110), (220, 220, 220), -1)
        cv2.putText(
            img,
            "TRAINING SESSION - DEMO",
            (160, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (30, 30, 30),
            2,
        )

        # Draw desks and chairs
        for row in range(3):
            for col in range(4):
                x = 80 + col * 130
                y = 160 + row * 90
                # Desk
                cv2.rectangle(img, (x, y), (x + 100, y + 45), (70, 70, 90), -1)
                # Simulated trainee circle
                cv2.circle(img, (x + 50, y + 25), 18, (120, 160, 220), -1)

        # Timestamp overlay
        timestamp = f"2026-10-08 10:00:{frame_idx // fps:02d}.{(frame_idx % fps) * 100:03d}"
        cv2.putText(
            img,
            f"CAM-01 [DEMO] {timestamp}",
            (20, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )

        out.write(img)

    out.release()
    return output_path


def clean_demo_data(db) -> None:
    """Removes all entities prefixed with DEMO."""
    print("[CLEAN] Searching for DEMO entities...")

    # Find demo centre
    centre = db.query(Centre).filter(Centre.centre_code == DEMO_CENTRE_CODE).first()
    if centre:
        db.delete(centre)
        print(f"  - Deleted demo centre {DEMO_CENTRE_CODE} and cascaded records.")

    # Find demo user
    user = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
    if user:
        db.delete(user)
        print(f"  - Deleted demo admin {DEMO_ADMIN_EMAIL}.")

    db.commit()
    print("[CLEAN] All DEMO data cleaned successfully.")


def seed_demo(db) -> None:
    """Inserts controlled DEMO records without fabricating AI accuracy metrics."""
    print("==========================================================")
    print("  SEEDING CONTROLLED SIH DEMO DATA")
    print("==========================================================")

    # 1. Demo User
    user = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
    if not user:
        user = User(
            name="[DEMO] Central Inspector",
            email=DEMO_ADMIN_EMAIL,
            password_hash=get_password_hash(DEMO_ADMIN_PASS),
            role="ADMIN",
            centre_id=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OK] Demo Admin Account created: {DEMO_ADMIN_EMAIL} (Password: {DEMO_ADMIN_PASS})")
    else:
        print(f"[INFO] Demo Admin already exists: {DEMO_ADMIN_EMAIL}")

    # 2. Demo Centre
    centre = db.query(Centre).filter(Centre.centre_code == DEMO_CENTRE_CODE).first()
    if not centre:
        centre = Centre(
            centre_code=DEMO_CENTRE_CODE,
            name=DEMO_CENTRE_NAME,
            location="Okhla Industrial Area Phase-III, New Delhi",
            status="ACTIVE",
        )
        db.add(centre)
        db.commit()
        db.refresh(centre)
        print(f"[OK] Demo Training Centre created: {centre.name} ({centre.centre_code})")
    else:
        print(f"[INFO] Demo Centre already exists: {centre.centre_code}")

    # 3. Demo Camera
    cam = db.query(Camera).filter(Camera.centre_id == centre.id, Camera.name == "[DEMO] Classroom Camera 01").first()
    if not cam:
        cam = Camera(
            centre_id=centre.id,
            name="[DEMO] Classroom Camera 01",
            source_type="VIDEO_FILE",
            source_url="data/input/demo_classroom_sample.mp4",
            is_active=True,
        )
        db.add(cam)
        db.commit()
        db.refresh(cam)
        print(f"[OK] Demo Camera registered: {cam.name}")
    else:
        print(f"[INFO] Demo Camera already exists: {cam.name}")

    # 4. Demo Sanctioned Inventory Baseline
    sanctioned_items = [
        {"item_name": "Computer", "category": "IT Lab", "expected_quantity": 20},
        {"item_name": "Chair", "category": "Classroom", "expected_quantity": 25},
        {"item_name": "Workbench", "category": "Workshop", "expected_quantity": 4},
        {"item_name": "Fire Extinguisher", "category": "Safety", "expected_quantity": 2},
    ]

    for item_data in sanctioned_items:
        existing_item = (
            db.query(InventoryItem)
            .filter(
                InventoryItem.centre_id == centre.id,
                InventoryItem.item_name == item_data["item_name"],
            )
            .first()
        )
        if not existing_item:
            inv = InventoryItem(
                centre_id=centre.id,
                item_name=item_data["item_name"],
                category=item_data["category"],
                expected_quantity=item_data["expected_quantity"],
            )
            db.add(inv)
            print(f"  + Sanctioned Inventory: {inv.item_name} (Expected: {inv.expected_quantity})")
    db.commit()

    # 5. Generate sample MP4 file for live upload demonstration
    sample_video_path = generate_sample_demo_video(DEMO_VIDEO_PATH, duration_sec=6, fps=10)
    print(f"[OK] Demo sample MP4 generated for upload demo: {sample_video_path}")

    # 6. Create initial unexecuted monitoring session ready for live test
    session = (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.centre_id == centre.id,
            MonitoringSession.camera_id == cam.id,
        )
        .first()
    )
    if not session:
        session = MonitoringSession(
            centre_id=centre.id,
            camera_id=cam.id,
            session_date=date.today(),
            physical_attendance=18,
            status="PENDING",
            created_by=user.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"[OK] Demo Monitoring Session #{session.id} created (Physical Attendance: {session.physical_attendance})")
    else:
        print(f"[INFO] Demo Monitoring Session #{session.id} already exists.")

    print("\n----------------------------------------------------------")
    print("DEMO SEED COMPLETED:")
    print(f"1. Login at /login with: {DEMO_ADMIN_EMAIL} / {DEMO_ADMIN_PASS}")
    print(f"2. View Centre at /centres/{centre.id}")
    print(f"3. Upload demo video '{DEMO_VIDEO_PATH}' at /monitoring/{session.id}")
    print("4. Trigger Snapshot Extraction -> Attendance AI -> Infra AI -> Compliance -> Alerts.")
    print("----------------------------------------------------------\n")


def main():
    parser = argparse.ArgumentParser(
        description="Controlled Demo Seeder for SIH Training Centre AI Monitoring"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly run the demo seeder to insert [DEMO] entities",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove all previously created [DEMO] entities from database",
    )

    args = parser.parse_args()

    if not args.execute and not args.clean:
        print("\n[SAFETY NOTICE]")
        print("This script is a controlled demo seeder. It will NOT run automatically.")
        print("To insert controlled [DEMO] entities, run:")
        print("    python scripts/seed_demo.py --execute\n")
        print("To clean up demo entities, run:")
        print("    python scripts/seed_demo.py --clean\n")
        sys.exit(0)

    db = SessionLocal()
    try:
        if args.clean:
            clean_demo_data(db)
        elif args.execute:
            seed_demo(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
