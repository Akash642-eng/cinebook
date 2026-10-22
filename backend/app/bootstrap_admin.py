from getpass import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_service import hash_password
from app.database import engine
from app.user_models import User


def main():
    with Session(engine) as db:
        existing_admin = db.scalar(
            select(User.id).where(User.role == "admin").limit(1)
        )

        if existing_admin is not None:
            print("An administrator already exists. No changes made.")
            return

        print("CineBook initial administrator setup")
        print("Use a new email address that is not already registered.")

        full_name = input("Administrator full name: ").strip()
        email = input("Administrator email: ").strip().lower()

        if len(full_name) < 2 or len(full_name) > 120:
            raise SystemExit("Name must be between 2 and 120 characters.")

        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise SystemExit(
                "That email already belongs to an account. "
                "Choose a new email; no account was changed."
            )

        password = getpass("Create administrator password (hidden): ")
        confirmation = getpass("Confirm administrator password (hidden): ")

        if password != confirmation:
            raise SystemExit("Passwords do not match. No account was created.")

        if len(password) < 16 or len(password) > 128:
            raise SystemExit(
                "Administrator password must be 16–128 characters."
            )

        admin = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("\nAdministrator created successfully.")
        print(f"User ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")
        print("Password was not displayed or stored in plaintext.")


if __name__ == "__main__":
    main()
