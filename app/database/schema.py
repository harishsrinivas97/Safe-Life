# app/database/schema.py
import logging
from .connection import get_db_connection

logger = logging.getLogger(__name__)


def init_db():
    """Create all required tables and run migration if needed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                email       TEXT    UNIQUE NOT NULL,
                phone_number TEXT,
                password    TEXT    NOT NULL,
                state       TEXT,
                chat_id     TEXT,
                role        TEXT    DEFAULT 'user',
                is_active   INTEGER DEFAULT 1,
                created_at  REAL    DEFAULT (julianday('now'))
            )
        """)

        # Profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER UNIQUE NOT NULL,
                age                TEXT,
                gender             TEXT,
                area               TEXT,
                city               TEXT,
                state              TEXT,
                blood_group        TEXT,
                diseases           TEXT,
                is_available       INTEGER DEFAULT 1,
                last_donation_date TEXT,
                updated_at         REAL    DEFAULT (julianday('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Blood requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blood_requests (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id     INTEGER NOT NULL,
                blood_group      TEXT    NOT NULL,
                hospital         TEXT,
                location         TEXT,
                city             TEXT,
                state            TEXT,
                required_units   INTEGER DEFAULT 1,
                urgency          TEXT    DEFAULT 'normal',
                message          TEXT,
                status           TEXT    DEFAULT 'pending',
                donors_contacted INTEGER DEFAULT 0,
                donors_accepted  INTEGER DEFAULT 0,
                created_at       REAL    DEFAULT (julianday('now')),
                FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Donor responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS donor_responses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id   INTEGER NOT NULL,
                donor_id     INTEGER NOT NULL,
                response     TEXT    DEFAULT 'pending',
                responded_at REAL,
                created_at   REAL    DEFAULT (julianday('now')),
                FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE,
                FOREIGN KEY (donor_id)   REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(request_id, donor_id)
            )
        """)

        # OTP verifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_verifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL,
                otp_hash   TEXT NOT NULL,
                expires_at REAL NOT NULL,
                used       INTEGER DEFAULT 0,
                created_at REAL    DEFAULT (julianday('now'))
            )
        """)

        conn.commit()
        logger.info('All tables created/verified.')

        _migrate_from_registration(conn, cursor)

    except Exception as exc:
        conn.rollback()
        logger.error('DB init failed: %s', exc)
        raise
    finally:
        cursor.close()
        conn.close()


def _migrate_from_registration(conn, cursor):
    """One-time migration from the old registration table."""
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registration'"
        )
        if not cursor.fetchone():
            return

        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] > 0:
            logger.info('Migration already done — skipping.')
            return

        logger.info('Running migration from registration table...')

        cursor.execute("""
            INSERT OR IGNORE INTO users
                (name, email, phone_number, password, state, chat_id)
            SELECT name, email, phone_number, password, state, chat_id
            FROM registration
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO profiles
                (user_id, age, gender, area, city, state, blood_group, diseases)
            SELECT u.id, r.age, r.gender, r.area, r.city, r.state,
                   r.blood_group, r.diseases
            FROM registration r
            JOIN users u ON u.email = r.email
        """)

        conn.commit()
        logger.info('Migration completed successfully.')

    except Exception as exc:
        logger.warning('Migration skipped: %s', exc)
