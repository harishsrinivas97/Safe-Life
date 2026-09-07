# app/routes/auth.py
import logging
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from app.database.connection import get_db_connection
from app.services.otp_service import generate_and_send_otp, verify_otp
from app.utils.validators import is_valid_email, is_valid_phone, is_strong_password
from app.extensions import limiter
import uuid

auth_bp = Blueprint('auth', __name__)
logger  = logging.getLogger(__name__)


def _is_profile_complete(conn, user_id: int) -> bool:
    """Return True if the user has filled all required profile fields."""
    cursor = conn.cursor()
    cursor.execute(
        'SELECT age, gender, blood_group, area, city FROM profiles WHERE user_id=?',
        (user_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return False
    return all([row['age'], row['gender'], row['blood_group'], row['area'], row['city']])


# ── REGISTER ────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('main.home'))

    errors = []
    form_data = {}

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        email        = request.form.get('email', '').strip().lower()
        phone_number = request.form.get('phone_number', '').strip()
        password     = request.form.get('password', '')
        state        = request.form.get('state', '').strip()
        form_data    = {'name': name, 'email': email, 'phone_number': phone_number, 'state': state}

        if not all([name, email, phone_number, password, state]):
            errors.append('All fields are required.')
        elif not is_valid_email(email):
            errors.append('Please enter a valid email address.')
        elif not is_valid_phone(phone_number):
            errors.append('Phone number must be exactly 10 digits.')
        else:
            strong, msg = is_strong_password(password)
            if not strong:
                errors.append(msg)

        if not errors:
            hashed  = generate_password_hash(password)
            chat_id = 'chat_' + uuid.uuid4().hex
            conn, cursor = None, None
            try:
                conn   = get_db_connection()
                cursor = conn.cursor()
                # Check duplicate email
                cursor.execute('SELECT id FROM users WHERE email=?', (email,))
                if cursor.fetchone():
                    errors.append('An account with this email already exists. Please log in.')
                else:
                    cursor.execute("""
                        INSERT INTO users (name, email, phone_number, password, state, chat_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (name, email, phone_number, hashed, state, chat_id))
                    conn.commit()
                    new_id = cursor.lastrowid
                    session['user_id']          = new_id
                    session['email']             = email
                    session['name']              = name
                    session['role']              = 'user'
                    session['profile_complete']  = False
                    flash('Registration successful! Please complete your profile.', 'success')
                    return redirect(url_for('profile.details'))
            except Exception as exc:
                logger.error('Registration error: %s', exc)
                errors.append('Registration failed. Please try again.')
            finally:
                if cursor: cursor.close()
                if conn:   conn.close()

    return render_template('register.html', errors=errors, form_data=form_data)


# ── LOGIN ────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if 'user_id' in session:
        return redirect(url_for('main.home'))

    errors = []
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn, cursor = None, None
        try:
            conn   = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email=? AND is_active=1', (email,))
            row  = cursor.fetchone()
            user = dict(row) if row else None

            if not user or not check_password_hash(user['password'], password):
                errors.append('Invalid email or password.')
            else:
                profile_ok = _is_profile_complete(conn, user['id'])
                session['user_id']          = user['id']
                session['email']             = user['email']
                session['name']              = user['name']
                session['role']              = user.get('role', 'user')
                session['profile_complete']  = profile_ok
                logger.info('User %s logged in.', email)

                if not profile_ok:
                    flash('Welcome back! Please complete your profile.', 'info')
                    return redirect(url_for('profile.details'))

                flash(f'Welcome back, {user["name"]}! 👋', 'success')
                return redirect(url_for('main.home'))

        except Exception as exc:
            logger.error('Login error: %s', exc)
            errors.append('Login failed. Please try again.')
        finally:
            if cursor: cursor.close()
            if conn:   conn.close()

    return render_template('login.html', errors=errors)


# ── LOGOUT ───────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    name = session.get('name', 'User')
    session.clear()
    flash(f'You have been logged out. See you soon, {name}!', 'info')
    return redirect(url_for('auth.login'))


# ── FORGOT PASSWORD ──────────────────────────────────────────────────────────
@auth_bp.route('/forgot', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def forgot():
    errors = []
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email or not is_valid_email(email):
            errors.append('Please enter a valid email address.')
        else:
            conn, cursor = None, None
            try:
                conn   = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE email=?', (email,))
                user = cursor.fetchone()
            finally:
                if cursor: cursor.close()
                if conn:   conn.close()

            # Always show success message to prevent email enumeration
            if user:
                if generate_and_send_otp(email):
                    session['reset_email'] = email
                else:
                    errors.append('Failed to send OTP. Please check email configuration.')

            if not errors:
                flash('If that email is registered, an OTP has been sent.', 'info')
                return redirect(url_for('auth.verify_otp_view'))

    return render_template('forgot.html', errors=errors)


# ── VERIFY OTP ───────────────────────────────────────────────────────────────
@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_view():
    email = session.get('reset_email')
    if not email:
        flash('Session expired. Please request a new OTP.', 'warning')
        return redirect(url_for('auth.forgot'))

    errors = []
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        if not entered_otp:
            errors.append('Please enter the OTP.')
        else:
            valid, msg = verify_otp(email, entered_otp)
            if valid:
                session['otp_verified'] = True
                flash('OTP verified successfully. Please set your new password.', 'success')
                return redirect(url_for('auth.reset_password_view'))
            else:
                errors.append(msg)

    return render_template('verify_otp.html', errors=errors, email=email)


# ── RESET PASSWORD ───────────────────────────────────────────────────────────
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_view():
    email    = session.get('reset_email')
    verified = session.get('otp_verified')

    if not email or not verified:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('auth.forgot'))

    errors = []
    if request.method == 'POST':
        new_pass     = request.form.get('new_password', '')
        confirm_pass = request.form.get('confirm_password', '')

        if not new_pass or not confirm_pass:
            errors.append('All fields are required.')
        elif new_pass != confirm_pass:
            errors.append('Passwords do not match.')
        else:
            strong, msg = is_strong_password(new_pass)
            if not strong:
                errors.append(msg)

        if not errors:
            hashed = generate_password_hash(new_pass)
            conn, cursor = None, None
            try:
                conn   = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET password=? WHERE email=?', (hashed, email)
                )
                conn.commit()
                session.pop('reset_email',  None)
                session.pop('otp_verified', None)
                flash('Password reset successful. Please log in with your new password.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as exc:
                logger.error('Password reset DB error: %s', exc)
                errors.append('Password reset failed. Please try again.')
            finally:
                if cursor: cursor.close()
                if conn:   conn.close()

    return render_template('reset_password.html', errors=errors)
