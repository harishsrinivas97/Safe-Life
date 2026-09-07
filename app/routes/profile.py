# app/routes/profile.py
import logging
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, jsonify
)
from app.database.connection import get_db_connection
from app.utils.decorators import login_required

profile_bp = Blueprint('profile', __name__)
logger     = logging.getLogger(__name__)

BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
DISEASES = [
    'None',
    'HIV/AIDS', 'Hepatitis B and C', 'Cancer',
    'Chronic Kidney Disease', 'Organ Transplant Recipients',
    'Diabetes', 'Chronic Heart Disease', 'Chronic Lung Disease',
    'Chronic Liver Disease', 'Blood Disorders', 'Autoimmune Diseases',
    'Epilepsy', 'Brucellosis', 'Chronic Infections',
    'Creutzfeldt-Jakob Disease', 'Severe Obesity'
]


def _get_user_profile(user_id: int):
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.phone_number, u.state, u.role,
                   p.age, p.gender, p.area, p.city, p.state as p_state,
                   p.blood_group, p.diseases, p.is_available, p.last_donation_date
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ── DETAILS (fill or update profile) ────────────────────────────────────────
@profile_bp.route('/details', methods=['GET', 'POST'])
@login_required
def details():
    user_id  = session['user_id']
    user     = _get_user_profile(user_id)
    errors   = []

    if request.method == 'POST':
        age        = request.form.get('age', '').strip()
        gender     = request.form.get('gender', '').strip()
        area       = request.form.get('area', '').strip()
        city       = request.form.get('city', '').strip()
        state      = request.form.get('state', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        diseases   = request.form.get('diseases', '').strip()

        if not all([age, gender, area, city, state, blood_group]):
            errors.append('All fields except diseases are required.')
        elif not age.isdigit() or not (1 <= int(age) <= 120):
            errors.append('Please enter a valid age (1–120).')
        elif blood_group not in BLOOD_GROUPS:
            errors.append('Please select a valid blood group.')
        else:
            diseases = diseases or 'None'
            conn, cursor = None, None
            try:
                conn   = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM profiles WHERE user_id=?', (user_id,)
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute("""
                        UPDATE profiles
                        SET age=?, gender=?, area=?, city=?, state=?,
                            blood_group=?, diseases=?, updated_at=julianday('now')
                        WHERE user_id=?
                    """, (age, gender, area, city, state,
                           blood_group, diseases, user_id))
                else:
                    cursor.execute("""
                        INSERT INTO profiles
                            (user_id, age, gender, area, city, state,
                             blood_group, diseases)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, age, gender, area, city, state,
                           blood_group, diseases))

                conn.commit()
                session['profile_complete'] = True
                flash('Profile updated successfully! 🎉', 'success')
                return redirect(url_for('main.home'))

            except Exception as exc:
                logger.error('Details update error: %s', exc)
                errors.append('Failed to save details. Please try again.')
            finally:
                if cursor: cursor.close()
                if conn:   conn.close()

    return render_template(
        'details.html',
        user=user,
        errors=errors,
        blood_groups=BLOOD_GROUPS,
        diseases=DISEASES
    )


# ── VIEW PROFILE ─────────────────────────────────────────────────────────────
@profile_bp.route('/profile')
@login_required
def view_profile():
    user = _get_user_profile(session['user_id'])
    if not user:
        flash('Profile not found.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('profile.html', user=user)


# ── TOGGLE DONOR AVAILABILITY ─────────────────────────────────────────────────
@profile_bp.route('/profile/toggle-availability', methods=['POST'])
@login_required
def toggle_availability():
    user_id = session['user_id']
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT is_available FROM profiles WHERE user_id=?', (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Profile not found.'}), 404

        new_status = 0 if row['is_available'] else 1
        cursor.execute(
            "UPDATE profiles SET is_available=?, updated_at=julianday('now') WHERE user_id=?",
            (new_status, user_id)
        )
        conn.commit()
        status_text = 'Available' if new_status else 'Unavailable'
        return jsonify({'success': True, 'is_available': new_status, 'status_text': status_text})

    except Exception as exc:
        logger.error('Toggle availability error: %s', exc)
        return jsonify({'success': False, 'message': 'Error updating status.'}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
