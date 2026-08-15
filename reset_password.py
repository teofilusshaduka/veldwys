#!/usr/bin/env python3
"""Reset a VeldWys account password from the machine holding the database.

Passwords are stored one-way, so there is nothing to recover — this sets a new one.
This is the break-glass path for accounts created before recovery questions existed;
everyone else uses the in-app "Forgot password?" flow.

    python reset_password.py <username> <new-password>
    python reset_password.py --list
"""
import sys

import db


def list_users() -> int:
    with db._conn() as conn:
        rows = conn.execute(
            "SELECT id, username, farm_name, password_salt FROM users ORDER BY id"
        ).fetchall()
    if not rows:
        print("No accounts in data/veldwys.db.")
        return 1
    print(f"{'id':>4}  {'username':<20} {'farm':<24} hashing")
    for r in rows:
        scheme = "pbkdf2" if (r["password_salt"] or "") else "legacy sha256"
        print(f"{r['id']:>4}  {r['username']:<20} {(r['farm_name'] or ''):<24} {scheme}")
    return 0


def reset(username: str, new_password: str) -> int:
    if len(new_password) < 4:
        print("Password must be at least 4 characters.")
        return 1
    with db._conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        print(f"No account named {username!r}. Run --list to see what exists.")
        return 1
    db.set_password(row["id"], new_password)
    if db.verify_user(username, new_password) != row["id"]:
        print("Reset wrote, but the new password did not verify. Nothing to trust here.")
        return 1
    print(f"Password reset for {username!r} (user id {row['id']}) and verified.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    db.init_db()
    if args and args[0] in ("--list", "-l"):
        return list_users()
    if len(args) != 2:
        print(__doc__.strip())
        return 1
    return reset(args[0], args[1])


if __name__ == "__main__":
    sys.exit(main())
