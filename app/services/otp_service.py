# app/services/otp_service.py
import random
import time
import hashlib
import logging
from app.database.connection import get_db_connection
from app.services.email_service import send_email, build_otp_email

logger = logging.getLogger(__name__)

OTP_TTL = 5 * 60  # 5 minutes


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def generate_and_send_otp(email: str) -> bool:
    """Generate a 6-digit OTP, store it in DB, and email it."""
    otp = f'{random.randint(100000, 999999):06d}'
    otp_hash  = _hash_otp(otp)
    expires_at = time.time() + OTP_TTL

    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Invalidate any existing OTPs for this email
        cursor.execute(
            'UPDATE otp_verifications SET used=1 WHERE email=? AND used=0',
            (email,)
        )

        # Insert new OTP
        cursor.execute(
            'INSERT INTO otp_verifications (email, otp_hash, expires_at) VALUES (?, ?, ?)',
            (email, otp_hash, expires_at)
        )
        conn.commit()

        # Send email
        subject  = 'BloodNeed – Your OTP for Password Reset'
        html     = build_otp_email(otp)
        success  = send_email(email, subject, html)

        if not success:
            logger.error('OTP email delivery failed for %s', email)
            return False

        logger.info('OTP generated and sent to %s', email)
        return True

    except Exception as exc:
        logger.error('OTP generation failed: %s', exc)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def verify_otp(email: str, entered_otp: str) -> tuple[bool, str]:
    """Verify the entered OTP. Returns (valid: bool, message: str)."""
    otp_hash = _hash_otp(entered_otp.strip())
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, expires_at, used
            FROM otp_verifications
            WHERE email=? AND otp_hash=?
            ORDER BY created_at DESC
            LIMIT 1
        """, (email, otp_hash))
        row = cursor.fetchone()

        if not row:
            return False, 'Invalid OTP. Please check and try again.'
        if row['used']:
            return False, 'This OTP has already been used.'
        if time.time() > row['expires_at']:
            return False, 'OTP has expired. Please request a new one.'

        # Mark as used
        cursor.execute(
            'UPDATE otp_verifications SET used=1 WHERE id=?',
            (row['id'],)
        )
        conn.commit()
        return True, 'OTP verified successfully.'

    except Exception as exc:
        logger.error('OTP verification error: %s', exc)
        return False, 'Verification failed. Please try again.'
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
