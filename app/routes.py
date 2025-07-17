import re
import uuid
import requests
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from .db import get_db_connection

load_dotenv()

bp = Blueprint('routes', __name__)

# Twilio & Telegram credentials — placeholder values removed
account_sid = 'your_SID_here'  
auth_token = 'your_auth_token_here'  
twilio_phone_number = 'your_twilio_phone_number_here'
telegram_token = 'your_telegram_token_here'
client = Client(account_sid, auth_token)

def format_phone(phone: str) -> str:
    return '+91' + phone if not phone.startswith('+') else phone

@bp.route('/')
def index():
    return redirect(url_for('routes.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    errors = []
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '')
        state = request.form.get('state', '').strip()

        full_phone = format_phone(phone_number)

        if not all([name, email, phone_number, password, state]):
            errors.append("All fields are required.")
        elif not re.fullmatch(r'\d{10}', phone_number):
            errors.append("Enter valid 10-digit phone number.")
        elif not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("Enter valid email address.")

        if not errors:
            hashed_password = generate_password_hash(password)
            chat_id = 'chat_' + uuid.uuid4().hex

            try:
                conn = get_db_connection()
                cursor = conn.cursor(buffered=True)
                cursor.execute("""
                    INSERT INTO registration (name, email, phone_number, password, state, chat_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name=VALUES(name), email=VALUES(email), password=VALUES(password), state=VALUES(state), chat_id=VALUES(chat_id)
                """, (name, email, full_phone, hashed_password, state, chat_id))
                conn.commit()
                cursor.close()
                conn.close()
                session['phone_number'] = full_phone
                return redirect(url_for('routes.login'))
            except Exception as e:
                errors.append("Registration failed: " + str(e))

    return render_template('register.html', errors=errors)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    errors = []
    if request.method == 'POST':
        raw_phone = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '')
        full_phone = format_phone(raw_phone)

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT password FROM registration WHERE phone_number = %s", (full_phone,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and check_password_hash(user['password'], password):
                session['phone_number'] = full_phone
                return redirect(url_for('routes.home'))
            else:
                errors.append("Invalid phone number or password.")
        except Exception as e:
            errors.append("Login failed: " + str(e))

    return render_template('login.html', errors=errors)

@bp.route('/home')
def home():
    if 'phone_number' not in session:
        return redirect(url_for('routes.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT name FROM registration WHERE phone_number = %s", (session['phone_number'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('home.html', name=user['name'])

@bp.route('/details', methods=['GET', 'POST'])
def details():
    if 'phone_number' not in session:
        return redirect(url_for('routes.login'))

    errors = []
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
        elif not age.isdigit() or int(age) <= 0:
            errors.append("Invalid age.")

        if not errors:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(buffered=True)
                cursor.execute("""
                    UPDATE registration 
                    SET name=%s, age=%s, gender=%s, area=%s, city=%s, state=%s, blood_group=%s, diseases=%s 
                    WHERE phone_number=%s
                """, (name, age, gender, area, city, state, blood_group, diseases, session['phone_number']))
                conn.commit()
                cursor.close()
                conn.close()
                flash("Details updated successfully.")
                return redirect(url_for('routes.home'))
            except Exception as e:
                errors.append("Update failed: " + str(e))

    return render_template('details.html', errors=errors)

@bp.route('/select-blood', methods=['GET', 'POST'])
def select_blood():
    if 'phone_number' not in session:
        return redirect(url_for('routes.login'))

    if request.method == 'POST':
        selected_groups = request.form.get('selected_groups')
        session['selected_groups'] = selected_groups

        if not selected_groups:
            flash('No blood groups selected.')
            return redirect(url_for('routes.select_blood'))

        blood_groups = selected_groups.split(',')
        requester_phone = session['phone_number']

        placeholders = ','.join(['%s'] * len(blood_groups))
        query = f"""
            SELECT phone_number 
            FROM registration 
            WHERE blood_group IN ({placeholders}) 
            AND phone_number != %s 
            AND diseases = 'None'
        """

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute(query, (*blood_groups, requester_phone))
            results = cursor.fetchall()
            if not results:
                flash("No donors found.")
            else:
                for (phone_number,) in results:
                    formatted_number = format_phone(phone_number)
                    body = (
                        f"A user with phone {requester_phone} requests your blood donation.\n"
                        f"Reply:\nYES - to donate\nNO - to decline"
                    )
                    try:
                        message = client.messages.create(
                            to=formatted_number,
                            from_=twilio_phone_number,
                            body=body
                        )
                        print(f"SMS sent to {formatted_number} - SID: {message.sid}")
                    except Exception as sms_error:
                        print(f"Failed to send SMS to {formatted_number}: {sms_error}")
                flash("Your request has been sent to matching donors!")
        except Exception as e:
            flash("Error searching donors: " + str(e))
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('routes.home'))

    return render_template('select_blood.html')

@bp.route('/twilio-sms', methods=['POST'])
def twilio_sms():
    from_number = request.form.get('From', '').strip()
    body = request.form.get('Body', '').strip().lower()

    print("Incoming SMS from:", from_number)
    print("Message body:", body)

    if not from_number or not body:
        return "Invalid request", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    if not from_number.startswith('+'):
        from_number = '+91' + from_number[-10:]

    cursor.execute("SELECT chat_id FROM registration WHERE phone_number = %s", (from_number,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return "Sender not found", 404

    chat_id = user['chat_id']
    donor_response = body.upper() if body in ['yes', 'no'] else 'INVALID'
    response_message = {
        'YES': "Thank you! We'll notify the requester.",
        'NO': "Thank you for your response.",
        'INVALID': "Invalid response. Please reply with YES or NO."
    }[donor_response]

    if donor_response in ['YES', 'NO']:
        try:
            cursor.execute("""
                INSERT INTO responses (phone_number, response, chat_id)
                VALUES (%s, %s, %s)
            """, (from_number, donor_response, chat_id))
            conn.commit()

            # Telegram alert
            requests.get(f"https://api.telegram.org/bot{telegram_token}/sendMessage", params={
                "chat_id": chat_id,
                "text": f"Response from {from_number}: {donor_response}"
            })
        except Exception as db_error:
            print("DB error:", db_error)

    cursor.close()
    conn.close()

    twiml_response = MessagingResponse()
    twiml_response.message(response_message)
    return str(twiml_response)

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('routes.login'))
