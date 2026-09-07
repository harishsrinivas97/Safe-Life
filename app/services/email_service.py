# app/services/email_service.py
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_SERVER   = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL  = os.getenv('SENDER_EMAIL', '')
SENDER_PASS   = os.getenv('SENDER_PASSWORD', '').replace(' ', '')


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via Gmail SMTP. Returns True on success."""
    if not SENDER_EMAIL or not SENDER_PASS:
        logger.warning('Email credentials not configured.')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'BloodNeed <{SENDER_EMAIL}>'
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())

        logger.info('Email sent to %s: %s', to_email, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error('SMTP authentication failed. Check SENDER_EMAIL and SENDER_PASSWORD.')
        return False
    except smtplib.SMTPException as exc:
        logger.error('SMTP error sending to %s: %s', to_email, exc)
        return False
    except Exception as exc:
        logger.error('Email send failed to %s: %s', to_email, exc)
        return False


def build_otp_email(otp: str) -> str:
    """Return a styled HTML email body for OTP delivery."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Inter, sans-serif; background:#f8f9fa; padding:40px 0;">
      <div style="max-width:480px; margin:0 auto; background:#fff; border-radius:16px;
                  box-shadow:0 4px 24px rgba(0,0,0,0.08); overflow:hidden;">
        <div style="background:#C0392B; padding:32px; text-align:center;">
          <h1 style="color:#fff; margin:0; font-size:24px; font-weight:700;">&#128149; BloodNeed</h1>
          <p style="color:rgba(255,255,255,0.85); margin:8px 0 0;">Password Reset Request</p>
        </div>
        <div style="padding:40px 32px;">
          <p style="color:#333; font-size:16px; margin-top:0;">Your one-time password (OTP) for password reset is:</p>
          <div style="background:#FDEDEC; border:2px dashed #C0392B; border-radius:12px;
                      padding:24px; text-align:center; margin:24px 0;">
            <span style="font-size:40px; font-weight:800; letter-spacing:12px; color:#C0392B;">{otp}</span>
          </div>
          <p style="color:#666; font-size:14px;">This OTP expires in <strong>5 minutes</strong>. Do not share it with anyone.</p>
          <p style="color:#999; font-size:12px; margin-top:32px; border-top:1px solid #eee; padding-top:16px;">
            If you did not request this, please ignore this email. Your account is safe.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
