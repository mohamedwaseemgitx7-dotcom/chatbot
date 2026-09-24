"""
Creates the values for the demo login (never store a plaintext password).

    backend/.venv/Scripts/python scripts/hash_password.py

Prompts for the password (not echoed) and prints lines to paste into backend/.env or Render:
    DEMO_PASSWORD_HASH=pbkdf2_sha256$600000$...
    SESSION_SECRET=<random 64 hex characters>   (only needed once per environment)
"""
import getpass
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.security.auth import hash_password  # noqa: E402

if __name__ == "__main__":
    password = getpass.getpass("Demo password: ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    print(f"DEMO_PASSWORD_HASH={hash_password(password)}")
    print(f"SESSION_SECRET={secrets.token_hex(32)}")
