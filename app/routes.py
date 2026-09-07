from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db_connection
from app.bmi import calculate_bmi_logic
from .reset_password_logic import generate_otp, verify_otp, reset_password_in_db
from .sms_utils import send_sms
import uuid
import re

bp = Blueprint('routes', __name__)

# ------------------- INDEX -------------------
@bp.route('/')
def index():
    return redirect(url_for('routes.login'))

# ------------------- REGISTER -------------------
@bp.route('/register', methods=['GET', 'POST'])
def register():
    errors = []
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '')
        state = request.form.get('state', '').strip()

        if not all([name, email, phone_number, password, state]):
            errors.append("All fields are required.")
        elif not re.fullmatch(r'\d{10}', phone_number):
            errors.append("Enter valid 10-digit phone number.")
        elif not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("Enter valid email address.")

        if not errors:
            hashed_password = generate_password_hash(password)
            chat_id = 'chat_' + uuid.uuid4().hex

            conn, cursor = None, None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO registration (name, email, phone_number, password, state, chat_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                        name=excluded.name,
                        phone_number=excluded.phone_number,
                        password=excluded.password,
                        state=excluded.state,
                        chat_id=excluded.chat_id
                """, (name, email, phone_number, hashed_password, state, chat_id))
                conn.commit()

                session['email'] = email
                flash("Registration successful! Please complete your details.")
                return redirect(url_for('routes.details'))

            except Exception as e:
                errors.append("Registration failed: " + str(e))
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    return render_template('register.html', errors=errors)

# ------------------- LOGIN -------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    errors = []
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn, cursor = None, None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM registration WHERE email = ?", (email,))
            row = cursor.fetchone()
            user = dict(row) if row else None
            if user and check_password_hash(user['password'], password):
                session['email'] = email

                required_fields = ['age', 'gender', 'blood_group', 'area', 'city', 'state', 'diseases']
                missing = any(not user.get(field) for field in required_fields)
                if missing:
                    flash("Please update your details before proceeding.")
                    return redirect(url_for('routes.details'))

                return redirect(url_for('routes.home'))
            else:
                errors.append("Invalid email or password.")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('login.html', errors=errors)

# ------------------- FORGOT PASSWORD -------------------
@bp.route('/forgot', methods=['GET', 'POST'])
def forgot():
    errors = []
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        conn, cursor = None, None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM registration WHERE email = ?", (email,))
            user = cursor.fetchone()
            if not user:
                errors.append("Email not found.")
            else:
                if generate_otp(email):
                    session['reset_email'] = email
                    flash("OTP sent to your email.")
                    return redirect(url_for('routes.reset_password_route'))
                else:
                    errors.append("Failed to send OTP email.")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return render_template('forgot.html', errors=errors)

# ------------------- RESET PASSWORD -------------------
@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_route():
    errors = []
    email = session.get('reset_email')
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not email:
            errors.append("Session expired. Please request a new OTP.")
        elif not entered_otp or not new_password or not confirm_password:
            errors.append("All fields are required.")
        elif new_password != confirm_password:
            errors.append("Passwords do not match.")
        else:
            valid, msg = verify_otp(email, entered_otp)
            if not valid:
                errors.append(msg)
            else:
                if reset_password_in_db(email, new_password):
                    flash("Password reset successful. Please log in.")
                    return redirect(url_for('routes.login'))
                else:
                    errors.append("Password reset failed. Try again.")

    return render_template('reset_password.html', errors=errors)

# ------------------- DETAILS UPDATE -------------------
@bp.route('/details', methods=['GET', 'POST'])
def details():
    if 'email' not in session:
        return redirect(url_for('routes.login'))

    errors = []
    email = session['email']
    conn, cursor = None, None
    user = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registration WHERE email=?", (email,))
        user = cursor.fetchone()

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            gender = request.form.get('gender', '').strip()
            area = request.form.get('area', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            blood_group = request.form.get('blood_group', '').strip()
            diseases = request.form.get('diseases', '').strip()

            if not all([name, age, gender, area, city, state, blood_group, diseases]):
                errors.append("All fields are required.")
            else:
                cursor.execute("""
                    UPDATE registration
                    SET name=?, age=?, gender=?, area=?, city=?, state=?,
                        blood_group=?, diseases=?
                    WHERE email=?
                """, (name, age, gender, area, city, state, blood_group, diseases, email))
                conn.commit()
                flash("Details updated successfully.")
                return redirect(url_for('routes.home'))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('details.html', errors=errors, user=user)

# ------------------- HOME -------------------
@bp.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' not in session:
        return redirect(url_for('routes.login'))

    conn, cursor = None, None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM registration WHERE email = ?", (session['email'],))
        user = cursor.fetchone()
        bmi_value, category = None, ""
        if request.method == 'POST':
            bmi_value, category = calculate_bmi_logic(request.form)
        return render_template('home.html', name=user['name'] if user else 'User', bmi=bmi_value, category=category)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ------------------- SELECT BLOOD -------------------
@bp.route('/select-blood', methods=['GET', 'POST'])
def select_blood():
    if 'email' not in session:
        return redirect(url_for('routes.login'))

    if request.method == 'POST':
        selected_groups = request.form.get('selected_groups')
        session['selected_groups'] = selected_groups

        if not selected_groups:
            flash('No blood groups selected.')
            return redirect(url_for('routes.select_blood'))

        blood_groups = [g.strip() for g in selected_groups.split(',') if g.strip()]
        requester_email = session['email']

        placeholders = ','.join(['?'] * len(blood_groups))
        query = f"""
            SELECT phone_number
            FROM registration
            WHERE blood_group IN ({placeholders})
            AND email != ?
        """

        conn, cursor = None, None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Fetch requester phone number safely
            cursor.execute("SELECT phone_number FROM registration WHERE email = ?", (requester_email,))
            requester_row = cursor.fetchone()
            if requester_row and requester_row[0]:
                requester_phone = requester_row[0]
            else:
                requester_phone = "Not Available"

            # Find matching donors
            cursor.execute(query, (*blood_groups, requester_email))
            results = cursor.fetchall()

            if not results:
                flash("No donors found for the selected blood groups.")
            else:
                for (phone_number,) in results:
                    body = (
                        f"A user with phone number {requester_phone} requests your blood donation.\n"
                        "Reply:\nYES - to donate\nNO - to decline"
                    )
                    try:
                        send_sms(phone_number, body)
                    except Exception:
                        flash(f"Failed to send SMS to {phone_number}. Check logs.")

                flash("Your request has been sent to matching donors!")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirect(url_for('routes.home'))

    return render_template('select_blood.html')

# ------------------- LOGOUT -------------------
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('routes.login'))
