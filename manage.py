"""Bootstrap helper: create an ADMIN user. Password comes from the environment."""
import os
import sys

from app import create_app
from app.db import get_db
from app.errors import utc_now
from app.services import create_user


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    password = os.environ.get("SGCM_ADMIN_PASSWORD")
    if not password:
        sys.exit("Set SGCM_ADMIN_PASSWORD in the environment")
    app = create_app()
    with app.app_context():
        create_user(get_db(), username, password, "ADMIN", utc_now())
    print(f"ADMIN '{username}' created")


if __name__ == "__main__":
    main()
