
import getpass

from werkzeug.security import generate_password_hash

from database import (
    initialize_admin_table,
    create_admin,
    get_admin_by_username,
)


def main():
    initialize_admin_table()

    print("\n=== CivicPulse AI: Create Admin ===")

    username = input("Enter admin username: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    if get_admin_by_username(username):
        print("This username already exists.")
        print("Choose another username or use your existing account.")
        return

    password = getpass.getpass("Enter admin password: ")
    confirm_password = getpass.getpass("Confirm admin password: ")

    if len(password) < 12:
        print("Password must be at least 12 characters long.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    password_hash = generate_password_hash(password)
    create_admin(username, password_hash)

    print("\nAdmin account created successfully!")
    print("Keep your password private.")


if __name__ == "__main__":
    main()
