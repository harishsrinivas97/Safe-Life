# app/utils/decorators.py
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def profile_required(f):
    """Redirect to details page if profile is not complete."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if not session.get('profile_complete'):
            flash('Please complete your profile first.', 'info')
            return redirect(url_for('profile.details'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Redirect if user is not an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated
