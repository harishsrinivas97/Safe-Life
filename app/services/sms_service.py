# app/services/sms_service.py
import os
import re
import logging

logger = logging.getLogger(__name__)


def _get_client():
    """Lazily create and return a Twilio client."""
    try:
        from twilio.rest import Client
        sid   = os.getenv('TWILIO_ACCOUNT_SID', '')
        token = os.getenv('TWILIO_AUTH_TOKEN', '')
        if not sid or not token or sid.startswith('your'):
            logger.warning('Twilio credentials not configured. SMS will be logged only.')
            return None
        return Client(sid, token)
    except ImportError:
        logger.warning('twilio package not installed.')
        return None


def send_sms(phone_number: str, body: str) -> bool:
    """Send an SMS via Twilio. Falls back to logging if not configured."""
    formatted = phone_number.strip()[-10:]
    if not re.fullmatch(r'\d{10}', formatted):
        logger.warning('Invalid phone number for SMS: %s', phone_number)
        return False

    to_number   = f'+91{formatted}'
    from_number = os.getenv('TWILIO_PHONE_NUMBER', '')

    client = _get_client()
    if not client:
        # Log the SMS instead of failing silently
        logger.info('[SMS STUB] To:%s | Body:%s', to_number, body)
        return True  # Return True so the flow continues

    try:
        message = client.messages.create(
            to=to_number,
            from_=from_number,
            body=body
        )
        logger.info('SMS sent to %s. SID: %s | Status: %s',
                    to_number, message.sid, message.status)
        return True
    except Exception as exc:
        logger.error('SMS failed to %s: %s', to_number, exc)
        return False


def build_blood_request_sms(requester_name: str, requester_city: str,
                             blood_group: str, urgency: str) -> str:
    """Build the SMS body for a blood donation request."""
    urgency_tag = '🚨 EMERGENCY' if urgency == 'emergency' else (
                  '⚠️ URGENT' if urgency == 'urgent' else 'Blood Donation Request')
    return (
        f"{urgency_tag} - BloodNeed\n"
        f"Blood Group Needed: {blood_group}\n"
        f"Location: {requester_city}\n"
        f"Reply YES to accept or NO to decline.\n"
        f"- BloodNeed Team"
    )
