# app/services/blood_matching.py
import logging
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)

# Which donor blood groups can donate to which recipient
DONOR_COMPATIBILITY = {
    'A+':  ['A+', 'AB+'],
    'A-':  ['A+', 'A-', 'AB+', 'AB-'],
    'B+':  ['B+', 'AB+'],
    'B-':  ['B+', 'B-', 'AB+', 'AB-'],
    'O+':  ['A+', 'B+', 'O+', 'AB+'],
    'O-':  ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'],
    'AB+': ['AB+'],
    'AB-': ['AB+', 'AB-'],
}

# Which donor blood groups can DONATE TO a specific recipient group
COMPATIBLE_DONORS = {
    'A+':  ['A+', 'A-', 'O+', 'O-'],
    'A-':  ['A-', 'O-'],
    'B+':  ['B+', 'B-', 'O+', 'O-'],
    'B-':  ['B-', 'O-'],
    'O+':  ['O+', 'O-'],
    'O-':  ['O-'],
    'AB+': ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'],
    'AB-': ['A-', 'B-', 'O-', 'AB-'],
}


def get_compatible_donors(recipient_blood_group: str, requester_user_id: int,
                           city: str = None, state: str = None):
    """
    Find compatible donors for a given recipient blood group.
    Returns list of dicts with user info, prioritized by location.
    """
    donor_groups = COMPATIBLE_DONORS.get(recipient_blood_group, [recipient_blood_group])
    if not donor_groups:
        return []

    placeholders = ','.join(['?'] * len(donor_groups))
    conn, cursor = None, None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        query = f"""
            SELECT
                u.id, u.name, u.phone_number, u.email,
                p.blood_group, p.city, p.state, p.area, p.is_available
            FROM users u
            JOIN profiles p ON p.user_id = u.id
            WHERE p.blood_group IN ({placeholders})
              AND p.is_available = 1
              AND u.id != ?
              AND u.is_active = 1
            ORDER BY
                CASE WHEN p.city  = ? THEN 0 ELSE 1 END,
                CASE WHEN p.state = ? THEN 0 ELSE 1 END,
                u.name
        """
        params = (*donor_groups, requester_user_id, city or '', state or '')
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    except Exception as exc:
        logger.error('Donor matching failed: %s', exc)
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
