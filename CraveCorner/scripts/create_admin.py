"""Create the first administrator account without storing a plain-text password."""

from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from werkzeug.security import generate_password_hash

from config import load_config
from database import connect


def main() -> int:
    config = load_config()
    username = input("Administrator username: ").strip()
    if not username or len(username) > 80:
        print("Username must contain between 1 and 80 characters.")
        return 1
    password = getpass("Password (at least 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 12:
        print("Choose a password with at least 12 characters.")
        return 1
    if password != confirmation:
        print("The passwords do not match.")
        return 1

    with connect(config["DATABASE"]) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """INSERT INTO admin_users (username, password_hash, created_at)
                   VALUES (?, ?, ?)""",
                (
                    username,
                    generate_password_hash(password),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            conn.commit()
        except Exception as error:
            conn.rollback()
            if "UNIQUE constraint failed" in str(error):
                print("That administrator username already exists.")
                return 1
            raise
    print(f"Administrator account '{username}' created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
