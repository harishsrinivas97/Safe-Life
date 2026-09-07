# app/reset_password_logic.py
import random
import time
from flask import session
from werkzeug.security import generate_password_hash
from .db import get_db_connection
from .email_utils import send_email

# In-memory OTP store
otp_store = {}
OTP_TTL_SECONDS = 5 * 60  # 5 minutes


def generate_otp(email: str) -> bool:
    """Generate OTP, store it, and send via email."""
    otp = f"{random.randint(100000, 999999):06d}"
    otp_store[email] = {"otp": otp, "expires": time.time() + OTP_TTL_SECONDS}

    subject = "Your OTP"
    body = f"Your OTP is: {otp}\nExpires in 5 minutes."

    return send_email(email, subject, body)


def verify_otp(email: str, entered_otp: str):
    """Verify if OTP is valid for the given email."""
    entry = otp_store.get(email)
    if not entry:
        return False, "OTP expired or not found."
    if time.time() > entry['expires']:
        otp_store.pop(email, None)
        return False, "OTP expired."
    if entry['otp'] != entered_otp:
        return False, "Invalid OTP."
    return True, ""


def reset_password_in_db(email: str, new_password: str) -> bool:
    """Update user password in the database."""
    hashed = generate_password_hash(new_password)
    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE registration SET password=? WHERE email=?", (hashed, email)
        )
        conn.commit()

        # Clean up OTP and session
        otp_store.pop(email, None)
        session.pop("reset_email", None)
        return True

    except Exception as e:
        print("Reset password failed:", e)
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
