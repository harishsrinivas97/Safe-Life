import os
import re
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

client = Client(account_sid, auth_token)

def send_sms(phone_number: str, body: str) -> bool:
    """Send SMS via Twilio."""
    try:
        formatted = phone_number[-10:]  # ensure last 10 digits
        if not re.fullmatch(r'\d{10}', formatted):
            print("Invalid phone number:", phone_number)
            return False
        to_number = "+91" + formatted
        message = client.messages.create(
            to=to_number,
            from_=twilio_phone_number,
            body=body
        )
        print(f"SMS sent to {to_number} - SID: {message.sid}")
        return True
    except Exception as exc:
        print(f"SMS send failed to {phone_number}: {exc}")
        return False
