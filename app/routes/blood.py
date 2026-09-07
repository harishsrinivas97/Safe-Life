# app/routes/blood.py
import logging
import time
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from app.database.connection import get_db_connection
from app.services.blood_matching import get_compatible_donors
from app.services.sms_service import send_sms, build_blood_request_sms
from app.utils.decorators import login_required, profile_required

blood_bp = Blueprint('blood', __name__)
logger   = logging.getLogger(__name__)

BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
UNIT_CHOICES  = list(range(1, 11))
URGENCY_CHOICES = [
    ('normal',    'Normal'),
    ('urgent',    'Urgent'),
    ('emergency', 'Emergency'),
]


# ── SELECT BLOOD / SEND REQUEST ──────────────────────────────────────────────
@blood_bp.route('/select-blood', methods=['GET', 'POST'])
@profile_required
def select_blood():
    user_id = session['user_id']
    errors  = []

    if request.method == 'POST':
        blood_group    = request.form.get('blood_group', '').strip()
        hospital       = request.form.get('hospital', '').strip()
        location       = request.form.get('location', '').strip()
        required_units = request.form.get('required_units', '1').strip()
        urgency        = request.form.get('urgency', 'normal').strip()
        message        = request.form.get('message', '').strip()

        if not blood_group or blood_group not in BLOOD_GROUPS:
            errors.append('Please select a valid blood group.')
        if not errors:
            conn, cursor = None, None
            try:
                conn   = get_db_connection()
                cursor = conn.cursor()

                # Get requester profile
                cursor.execute("""
                    SELECT u.name, u.phone_number,
                           p.city, p.state
                    FROM users u
                    LEFT JOIN profiles p ON p.user_id = u.id
                    WHERE u.id = ?
                """, (user_id,))
                requester = cursor.fetchone()
                city  = requester['city']  if requester else ''
                state = requester['state'] if requester else ''
                name  = requester['name']  if requester else 'User'

                # Find compatible donors
                donors = get_compatible_donors(blood_group, user_id, city, state)

                # Create blood request record
                cursor.execute("""
                    INSERT INTO blood_requests
                        (requester_id, blood_group, hospital, location,
                         city, state, required_units, urgency, message,
                         donors_contacted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, blood_group, hospital, location,
                    city, state,
                    int(required_units) if required_units.isdigit() else 1,
                    urgency, message, len(donors)
                ))
                request_id = cursor.lastrowid

                # Send SMS to each donor and record response
                sms_body   = build_blood_request_sms(name, city, blood_group, urgency)
                sent_count = 0
                for donor in donors:
                    send_sms(donor['phone_number'], sms_body)
                    sent_count += 1
                    # Record donor response (pending)
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO donor_responses
                                (request_id, donor_id, response)
                            VALUES (?, ?, 'pending')
                        """, (request_id, donor['id']))
                    except Exception:
                        pass

                conn.commit()

                if donors:
                    flash(
                        f'Blood request sent to {sent_count} matching donors! '
                        'They will be notified via SMS.',
                        'success'
                    )
                else:
                    flash(
                        'No matching donors found in the system right now. '
                        'Your request has been recorded.',
                        'warning'
                    )
                return redirect(url_for('blood.my_requests'))

            except Exception as exc:
                logger.error('Blood request error: %s', exc)
                errors.append('Failed to send request. Please try again.')
            finally:
                if cursor: cursor.close()
                if conn:   conn.close()

    return render_template(
        'select_blood.html',
        blood_groups=BLOOD_GROUPS,
        unit_choices=UNIT_CHOICES,
        urgency_choices=URGENCY_CHOICES,
        errors=errors
    )


# ── MY REQUESTS ───────────────────────────────────────────────────────────────
@blood_bp.route('/my-requests')
@login_required
def my_requests():
    user_id = session['user_id']
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT br.*,
                   (SELECT COUNT(*) FROM donor_responses
                    WHERE request_id=br.id AND response='accepted') as accepted,
                   (SELECT COUNT(*) FROM donor_responses
                    WHERE request_id=br.id AND response='declined') as declined,
                   (SELECT COUNT(*) FROM donor_responses
                    WHERE request_id=br.id AND response='pending')  as pending
            FROM blood_requests br
            WHERE br.requester_id = ?
            ORDER BY br.created_at DESC
        """, (user_id,))
        requests = cursor.fetchall()
        return render_template('requester_dashboard.html', requests=requests)
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ── DONOR DASHBOARD ───────────────────────────────────────────────────────────
@blood_bp.route('/donor-dashboard')
@login_required
def donor_dashboard():
    user_id = session['user_id']
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Get donor's blood group
        cursor.execute('SELECT blood_group, is_available FROM profiles WHERE user_id=?',
                       (user_id,))
        profile = cursor.fetchone()

        # Requests matching this donor's blood group
        active_requests = []
        my_responses    = []
        if profile and profile['blood_group']:
            cursor.execute("""
                SELECT br.id, br.blood_group, br.hospital, br.city,
                       br.urgency, br.status, br.required_units,
                       br.created_at, u.name as requester_name,
                       (
                           SELECT response FROM donor_responses
                           WHERE request_id=br.id AND donor_id=?
                       ) as my_response
                FROM blood_requests br
                JOIN users u ON u.id = br.requester_id
                WHERE br.blood_group = ? AND br.status = 'pending'
                  AND br.requester_id != ?
                ORDER BY br.urgency DESC, br.created_at DESC
                LIMIT 20
            """, (user_id, profile['blood_group'], user_id))
            active_requests = cursor.fetchall()

            cursor.execute("""
                SELECT dr.response, dr.responded_at, br.blood_group,
                       br.hospital, br.city, br.urgency, br.created_at,
                       u.name as requester_name
                FROM donor_responses dr
                JOIN blood_requests br ON br.id = dr.request_id
                JOIN users u ON u.id = br.requester_id
                WHERE dr.donor_id = ?
                ORDER BY dr.created_at DESC
                LIMIT 20
            """, (user_id,))
            my_responses = cursor.fetchall()

        return render_template(
            'donor_dashboard.html',
            profile=profile,
            active_requests=active_requests,
            my_responses=my_responses
        )
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ── RESPOND TO REQUEST ────────────────────────────────────────────────────────
@blood_bp.route('/respond/<int:request_id>', methods=['POST'])
@login_required
def respond(request_id):
    user_id  = session['user_id']
    response = request.form.get('response', '').lower()

    if response not in ('accepted', 'declined'):
        flash('Invalid response.', 'danger')
        return redirect(url_for('blood.donor_dashboard'))

    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO donor_responses (request_id, donor_id, response, responded_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(request_id, donor_id) DO UPDATE SET
                response=excluded.response,
                responded_at=excluded.responded_at
        """, (request_id, user_id, response, time.time()))

        if response == 'accepted':
            cursor.execute("""
                UPDATE blood_requests SET donors_accepted=donors_accepted+1
                WHERE id=?
            """, (request_id,))

        conn.commit()
        msg = 'Thank you for accepting! The requester will be notified.' \
              if response == 'accepted' else 'Response recorded.'
        flash(msg, 'success' if response == 'accepted' else 'info')

    except Exception as exc:
        logger.error('Respond error: %s', exc)
        flash('Failed to submit response.', 'danger')
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    return redirect(url_for('blood.donor_dashboard'))
