# app/routes/main.py
import logging
from flask import (
    Blueprint, render_template, redirect, url_for, session
)
from app.database.connection import get_db_connection
from app.utils.decorators import login_required, admin_required

main_bp = Blueprint('main', __name__)
logger  = logging.getLogger(__name__)


@main_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.home'))
    return redirect(url_for('auth.login'))


@main_bp.route('/home')
@login_required
def home():
    user_id = session['user_id']
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # User + profile info
        cursor.execute("""
            SELECT u.name, u.email, u.phone_number,
                   p.blood_group, p.city, p.state, p.is_available
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id = ?
        """, (user_id,))
        user = cursor.fetchone()

        # Stats
        cursor.execute(
            'SELECT COUNT(*) FROM blood_requests WHERE requester_id=?', (user_id,)
        )
        total_requests = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM donor_responses dr
            JOIN blood_requests br ON br.id = dr.request_id
            WHERE br.requester_id = ? AND dr.response = 'accepted'
        """, (user_id,))
        accepted_donors = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM blood_requests br
            JOIN profiles p ON p.blood_group = br.blood_group
            WHERE p.user_id = ? AND br.requester_id != ?
              AND br.status = 'pending'
        """, (user_id, user_id))
        matching_requests = cursor.fetchone()[0]

        # Recent requests
        cursor.execute("""
            SELECT br.id, br.blood_group, br.city, br.urgency,
                   br.status, br.created_at, br.donors_contacted
            FROM blood_requests br
            WHERE br.requester_id = ?
            ORDER BY br.created_at DESC
            LIMIT 5
        """, (user_id,))
        recent_requests = cursor.fetchall()

        return render_template(
            'home.html',
            user=user,
            total_requests=total_requests,
            accepted_donors=accepted_donors,
            matching_requests=matching_requests,
            recent_requests=recent_requests
        )
    except Exception as exc:
        logger.error('Home page error: %s', exc)
        return render_template(
            'home.html',
            user=None,
            total_requests=0,
            accepted_donors=0,
            matching_requests=0,
            recent_requests=[]
        )
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@main_bp.route('/admin')
@admin_required
def admin():
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM blood_requests')
        total_requests = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM blood_requests WHERE status='pending'")
        pending_requests = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM blood_requests WHERE urgency='emergency'")
        emergency_requests = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM profiles WHERE is_available=1")
        available_donors = cursor.fetchone()[0]

        # Recent users
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.is_active, u.created_at,
                   p.blood_group, p.city
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            ORDER BY u.created_at DESC
            LIMIT 20
        """)
        users = cursor.fetchall()

        # Recent requests
        cursor.execute("""
            SELECT br.id, br.blood_group, br.urgency, br.status,
                   br.city, br.created_at, u.name as requester_name
            FROM blood_requests br
            JOIN users u ON u.id = br.requester_id
            ORDER BY br.created_at DESC
            LIMIT 20
        """)
        requests = cursor.fetchall()

        return render_template(
            'admin_dashboard.html',
            total_users=total_users,
            total_requests=total_requests,
            pending_requests=pending_requests,
            emergency_requests=emergency_requests,
            available_donors=available_donors,
            users=users,
            requests=requests
        )
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main_bp.app_errorhandler(500)
def server_error(e):
    logger.error('500 error: %s', e)
    return render_template('500.html'), 500
