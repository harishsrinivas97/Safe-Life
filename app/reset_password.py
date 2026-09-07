# app/reset_password.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .reset_password_logic import generate_otp, verify_otp, reset_password_in_db

# Blueprint definition
reset_bp = Blueprint('reset_routes', __name__, url_prefix='/reset')

# ------------------- FORGOT PASSWORD (send OTP) -------------------
@reset_bp.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    errors = []
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            errors.append("Email is required.")
        else:
            success = generate_otp(email)
            if success:
                session['reset_email'] = email
                flash("OTP sent to your email.")
                return redirect(url_for('reset_routes.verify_otp_route'))
            else:
                errors.append("Failed to send OTP. Check email configuration.")

    return render_template('forgot_password.html', errors=errors)


# ------------------- VERIFY OTP -------------------
@reset_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_route():
    errors = []
    email = session.get('reset_email')
    if not email:
        flash("Session expired. Please request a new OTP.")
        return redirect(url_for('reset_routes.forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        is_valid, msg = verify_otp(email, entered_otp)
        if is_valid:
            flash("OTP verified. Please set a new password.")
            return redirect(url_for('reset_routes.reset_password_route'))
        else:
            errors.append(msg)

    return render_template('verify_otp.html', errors=errors)


# ------------------- RESET PASSWORD -------------------
@reset_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_route():
    errors = []
    email = session.get('reset_email')
    if not email:
        flash("Session expired. Please request a new OTP.")
        return redirect(url_for('reset_routes.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not new_password or not confirm_password:
            errors.append("All fields are required.")
        elif new_password != confirm_password:
            errors.append("Passwords do not match.")
        else:
            success = reset_password_in_db(email, new_password)
            if success:
                flash("Password reset successful. Please login.")
                return redirect(url_for('routes.login'))
            else:
                errors.append("Failed to reset password. Try again later.")

    return render_template('reset_password.html', errors=errors)
