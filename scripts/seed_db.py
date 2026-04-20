"""Seed a notify-server database with test data.

Creates users, services, subscriptions, and notifications, then writes
JWT tokens to a JSON file that Locust (or manual testing) can consume.

Usage:
    python scripts/seed_db.py [OPTIONS]

The script imports models directly from the app but avoids importing
app.utils (which pulls in ios/firebase modules that need credentials).
"""

import argparse
import datetime
import json
import random
import uuid

import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Notification,
    Service,
    User,
    UserNotification,
    users_services_table,
)
from app.settings import JWT_ALGORITHM, SECRET_KEY, SQLALCHEMY_DATABASE_URL

SERVICE_CATEGORIES = [
    "Accelerator Status",
    "Beamline BioMAX",
    "Beamline NanoMAX",
    "Beamline Balder",
    "Beamline CoSAXS",
    "Beamline DanMAX",
    "Beamline FemtoMAX",
    "IT Services",
    "Safety Alerts",
    "Facility News",
    "Machine Status",
    "User Office",
    "Experiment Scheduling",
    "Detector Systems",
    "Vacuum Systems",
]

COLORS = [
    "FF6B6B",
    "4ECDC4",
    "45B7D1",
    "96CEB4",
    "FFEAA7",
    "DDA0DD",
    "98D8C8",
    "F7DC6F",
    "BB8FCE",
    "85C1E9",
    "F0B27A",
    "82E0AA",
    "F1948A",
    "AED6F1",
    "D5DBDB",
]

NOTIFICATION_TEMPLATES = [
    ("Scheduled maintenance", "Maintenance window for {service} starting soon"),
    ("Status update", "{service}: all systems operational"),
    ("Alert", "Attention: {service} reporting anomalous readings"),
    ("Reminder", "Upcoming experiment session on {service}"),
    ("Resolution", "Issue on {service} has been resolved"),
    ("Configuration change", "{service} parameters have been updated"),
    ("New publication", "New results published from {service}"),
    ("Downtime notice", "{service} will be unavailable for scheduled work"),
]


def create_access_token(username: str, expire: datetime.datetime) -> str:
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, str(SECRET_KEY), algorithm=JWT_ALGORITHM)


def parse_args():
    parser = argparse.ArgumentParser(description="Seed the notify-server database")
    parser.add_argument(
        "--db-url",
        default=str(SQLALCHEMY_DATABASE_URL),
        help="SQLAlchemy database URL (default: from SQLALCHEMY_DATABASE_URL env)",
    )
    parser.add_argument(
        "--clear", action="store_true", help="Drop existing data before seeding"
    )
    parser.add_argument("--num-users", type=int, default=50)
    parser.add_argument("--num-services", type=int, default=10)
    parser.add_argument("--num-notifications", type=int, default=500)
    parser.add_argument(
        "--output-tokens",
        default="scripts/test_tokens.json",
        help="Path to write the generated tokens JSON",
    )
    return parser.parse_args()


def seed(args):
    now = datetime.datetime.now(datetime.timezone.utc)
    token_expire = now + datetime.timedelta(days=30)

    connect_args = {}
    if args.db_url.startswith("sqlite:"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(args.db_url, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    if args.clear:
        print("Clearing existing data...")
        db.execute(users_services_table.delete())
        db.query(UserNotification).delete()
        db.query(Notification).delete()
        db.query(Service).delete()
        db.query(User).delete()
        db.commit()

    # --- Services ---
    categories = SERVICE_CATEGORIES[: args.num_services]
    services = []
    for i, category in enumerate(categories):
        s = Service(
            id=uuid.uuid4(),
            category=category,
            color=COLORS[i % len(COLORS)],
            owner="test-owner",
        )
        services.append(s)
    db.add_all(services)
    db.flush()
    print(f"Created {len(services)} services")

    # --- Users ---
    users = []
    for i in range(1, args.num_users + 1):
        username = f"testuser_{i:03d}"
        u = User(
            username=username,
            is_admin=(i == 1),
            is_active=True,
            login_token_expire_date=token_expire,
        )
        users.append(u)
    db.add_all(users)
    db.flush()
    print(f"Created {len(users)} users")

    # --- Subscriptions ---
    subscriptions = []
    for user in users:
        n_subs = random.randint(2, min(5, len(services)))
        for service in random.sample(services, n_subs):
            subscriptions.append({"user_id": user.id, "service_id": service.id})
    db.execute(users_services_table.insert(), subscriptions)
    db.flush()
    print(f"Created {len(subscriptions)} subscriptions")

    # Build a lookup: service_id -> list of subscriber user_ids
    subs_by_service = {}
    for sub in subscriptions:
        subs_by_service.setdefault(sub["service_id"], []).append(sub["user_id"])

    # --- Notifications + UserNotification rows ---
    un_table = UserNotification.__table__
    n_created = 0
    batch_size = 100
    un_rows = []
    for i in range(args.num_notifications):
        service = random.choice(services)
        title, subtitle_tpl = random.choice(NOTIFICATION_TEMPLATES)
        subtitle = subtitle_tpl.format(service=service.category)
        days_ago = random.uniform(0, 30)
        timestamp = now - datetime.timedelta(days=days_ago)

        notification = Notification(
            title=title,
            subtitle=subtitle,
            url=f"https://notify.example.com/n/{i + 1}",
            service_id=service.id,
            timestamp=timestamp,
        )
        db.add(notification)
        db.flush()

        subscriber_ids = subs_by_service.get(service.id, [])
        for user_id in subscriber_ids:
            un_rows.append(
                {
                    "user_id": user_id,
                    "notification_id": notification.id,
                    "is_read": random.random() < 0.3,
                }
            )

        n_created += 1
        if n_created % batch_size == 0:
            if un_rows:
                db.execute(un_table.insert(), un_rows)
                un_rows = []
            db.flush()
            print(f"  ... {n_created}/{args.num_notifications} notifications")

    if un_rows:
        db.execute(un_table.insert(), un_rows)
    db.commit()
    print(f"Created {n_created} notifications")

    # --- Generate tokens ---
    token_data = {
        "admin_token": create_access_token("testuser_001", token_expire),
        "user_tokens": [create_access_token(u.username, token_expire) for u in users],
        "users": [
            {
                "username": u.username,
                "token": create_access_token(u.username, token_expire),
            }
            for u in users
        ],
        "service_ids": [str(s.id) for s in services],
    }
    with open(args.output_tokens, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"Tokens written to {args.output_tokens}")

    db.close()


if __name__ == "__main__":
    args = parse_args()
    seed(args)
