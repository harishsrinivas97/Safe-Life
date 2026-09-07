# app/utils/validators.py
import re


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r'\d{10}', phone.strip()))


def is_strong_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter.'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one number.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', password):
        return False, 'Password must contain at least one special character.'
    return True, ''


def sanitize_text(text: str) -> str:
    """Strip extra whitespace from text input."""
    return text.strip() if text else ''
