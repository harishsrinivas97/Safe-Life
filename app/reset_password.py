# app/reset_password.py
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from twilio.rest import Client
from .db import get_db_connection

reset_bp = Blueprint('reset_routes', __name__)

# Twilio configuration (HARD-CODED - NOT RECOMMENDED FOR PRODUCTION)
account_sid = 'your_real_sid_here'
auth_token = 'your_real_auth_token_here'
twilio_phone_number = '+1xxxxxxxxxx'  # Your Twilio number with country code
client = Client(account_sid, auth_token)

def format_phone(phone: str) -> str:
    return '+91' + phone if not phone.startswith('+') else phone

@reset_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    errors = []
    if request.method == 'POST':
        phone = request.form.get('phone_number', '').strip()
        full_phone = format_phone(phone)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM registration WHERE phone_number = %s", (full_phone,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            otp = str(uuid.uuid4().hex[:6]).upper()
            session['reset_otp'] = otp
            session['reset_phone'] = full_phone

            try:
                client.messages.create(
                    to=full_phone,
                    from_=twilio_phone_number,
                    body=f"Your OTP for password reset is: {otp}"
                )
                flash("OTP sent to your registered phone number.")
                return redirect(url_for('reset_routes.verify_otp'))
            except Exception:
                flash("Something went wrong while sending OTP.")
        else:
            errors.append("Phone number not registered.")
    return render_template('forgot_password.html', errors=errors)

@reset_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    errors = []
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip().upper()
        if entered_otp == session.get('reset_otp'):
            return redirect(url_for('reset_routes.reset_password'))
        else:
            errors.append("Invalid OTP.")
    return render_template('verify_otp.html', errors=errors)

@reset_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    errors = []
    if 'reset_phone' not in session:
        flash("Session expired. Please try again.")
        return redirect(url_for('reset_routes.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not password or not confirm:
            errors.append("Please fill out both fields.")
        elif password != confirm:
            errors.append("Passwords do not match.")
        else:
            hashed = generate_password_hash(password)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE registration SET password = %s WHERE phone_number = %s", (hashed, session['reset_phone']))
            conn.commit()
            cursor.close()
            conn.close()

            flash("Password reset successful. You can now log in.")
            session.pop('reset_phone', None)
            session.pop('reset_otp', None)
            return redirect(url_for('routes.login'))

    return render_template('reset_password.html', errors=errors)
