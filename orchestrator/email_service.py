"""
Email Notification Service using smtplib.
Sends email notifications for scheduled interviews and other events.
"""

import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP using smtplib."""

    def __init__(self):
        self.settings = get_settings()

    def send_interview_confirmation(
        self,
        candidate_name: str,
        candidate_email: str,
        interview_date: str,
        interview_time: str,
        interviewer_name: str,
        schedule_id: str,
        notes: str | None = None,
    ) -> tuple[bool, str]:
        """
        Send a confirmation email for a scheduled interview using smtplib.

        Args:
            candidate_name: Name of the candidate
            candidate_email: Email address of the candidate
            interview_date: Date string (e.g., "August 12, 2026")
            interview_time: Time string (e.g., "10:00 AM UTC")
            interviewer_name: Name/ID of the assigned interviewer
            schedule_id: Unique schedule ID
            notes: Optional additional notes

        Returns:
            tuple[bool, str]: (Success boolean, Status/error message string)
        """
        sender_email = self.settings.smtp_from_email or "notifications@intelliview.ai"
        host = self.settings.smtp_host or "localhost"
        port = self.settings.smtp_port or 1025

        # Sanitize HTML inputs to prevent injection vulnerabilities
        safe_name = html.escape(candidate_name)
        safe_email = html.escape(candidate_email)
        safe_date = html.escape(interview_date)
        safe_time = html.escape(interview_time)
        safe_interviewer = html.escape(interviewer_name)
        safe_sched_id = html.escape(schedule_id)
        safe_notes = html.escape(notes) if notes else ""

        subject = f"Interview Scheduled: AI Interview Session ({safe_date})"

        # Plain text fallback
        text_body = f"""Dear {candidate_name},

Your interview has been successfully scheduled!

Interview Details:
------------------
Schedule ID: {schedule_id}
Candidate: {candidate_name} ({candidate_email})
Date: {interview_date}
Time: {interview_time}
Interviewer: {interviewer_name}
{f'Notes: {notes}' if notes else ''}

Please make sure to join on time. 

Best regards,
IntelliView Interview Team
"""

        # HTML Email format
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #09090b; color: #f4f4f5; margin: 0; padding: 20px; }}
    .card {{ max-width: 600px; margin: 0 auto; background-color: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
    .header {{ border-bottom: 1px solid #27272a; padding-bottom: 16px; margin-bottom: 20px; }}
    .header h2 {{ color: #6366f1; margin: 0; font-size: 22px; }}
    .footer {{ margin-top: 24px; border-top: 1px solid #27272a; padding-top: 16px; font-size: 12px; color: #71717a; text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2>🎉 Interview Confirmation</h2>
      <p style="color: #a1a1aa; font-size: 14px; margin-top: 4px;">Your AI technical interview has been scheduled.</p>
    </div>

    <p style="font-size: 15px;">Dear <strong>{safe_name}</strong>,</p>
    <p style="font-size: 14px; color: #d4d4d8;">We are pleased to invite you to your upcoming technical interview session. Below are the details:</p>

    <div style="background-color: #27272a; border-radius: 8px; padding: 16px; margin: 20px 0;">
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 6px 0; color: #a1a1aa; font-size: 14px; width: 130px;">Schedule ID:</td>
          <td style="padding: 6px 0; color: #f4f4f5; font-size: 14px; font-family: monospace;">{safe_sched_id}</td>
        </tr>
        <tr>
          <td style="padding: 6px 0; color: #a1a1aa; font-size: 14px;">Candidate:</td>
          <td style="padding: 6px 0; color: #f4f4f5; font-size: 14px;"><strong>{safe_name}</strong> ({safe_email})</td>
        </tr>
        <tr>
          <td style="padding: 6px 0; color: #a1a1aa; font-size: 14px;">Date:</td>
          <td style="padding: 6px 0; color: #38bdf8; font-size: 14px; font-weight: 600;">{safe_date}</td>
        </tr>
        <tr>
          <td style="padding: 6px 0; color: #a1a1aa; font-size: 14px;">Time:</td>
          <td style="padding: 6px 0; color: #38bdf8; font-size: 14px; font-weight: 600;">{safe_time}</td>
        </tr>
        <tr>
          <td style="padding: 6px 0; color: #a1a1aa; font-size: 14px;">Interviewer:</td>
          <td style="padding: 6px 0; color: #f4f4f5; font-size: 14px;">{safe_interviewer}</td>
        </tr>
        {f'<tr><td style="padding: 6px 0; color: #a1a1aa; font-size: 14px;">Notes:</td><td style="padding: 6px 0; color: #e4e4e7; font-size: 14px;">{safe_notes}</td></tr>' if safe_notes else ''}
      </table>
    </div>

    <p style="font-size: 14px; color: #a1a1aa;">Please ensure your camera and microphone are ready prior to the interview time.</p>

    <div class="footer">
      IntelliView AI Interview Platform &bull; Automated Notification
    </div>
  </div>
</body>
</html>
"""

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = candidate_email

        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            logger.info(
                f"Attempting to send email via SMTP to candidate via {host}:{port}"
            )
            # Use SSL if port 465, otherwise standard SMTP with optional TLS
            if port == 465:
                with smtplib.SMTP_SSL(host=host, port=port, timeout=10) as server:
                    if self.settings.smtp_user and self.settings.smtp_password:
                        server.login(
                            self.settings.smtp_user, self.settings.smtp_password
                        )
                    server.send_message(message)
            else:
                with smtplib.SMTP(host=host, port=port, timeout=10) as server:
                    if self.settings.smtp_use_tls:
                        server.starttls()
                    if self.settings.smtp_user and self.settings.smtp_password:
                        server.login(
                            self.settings.smtp_user, self.settings.smtp_password
                        )
                    server.send_message(message)

            logger.info("Email notification successfully dispatched.")
            return True, "Email sent successfully"

        except Exception as e:
            error_msg = f"Failed to send email notification: {e!s}"
            logger.warning(error_msg)
            return False, error_msg

    def send_verification_email(
        self,
        candidate_name: str,
        candidate_email: str,
        token: str,
    ) -> tuple[bool, str]:
        """
        Send an email verification link to a registered candidate.
        """
        import os

        sender_email = self.settings.smtp_from_email or "notifications@intelliview.ai"
        host = self.settings.smtp_host or "localhost"
        port = self.settings.smtp_port or 1025
        base_url = getattr(self.settings, "app_base_url", "http://localhost:8000")

        # Sanitize HTML inputs
        safe_name = html.escape(candidate_name)
        safe_email = html.escape(candidate_email)
        safe_token = html.escape(token)

        # Verification URL
        verification_url = f"{base_url}/verify-email?token={safe_token}"

        subject = "Please Verify Your Email - IntelliView"

        # Plain text fallback
        text_body = f"""Dear {candidate_name},

Please verify your email address to complete your registration and book your interview.

Click the link below to verify:
{verification_url}

This link will expire in 24 hours.

Best regards,
IntelliView Team
"""

        # HTML body fallback
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #09090b; color: #f4f4f5; margin: 0; padding: 20px; }}
    .card {{ max-width: 600px; margin: 0 auto; background-color: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
    .header {{ border-bottom: 1px solid #27272a; padding-bottom: 16px; margin-bottom: 20px; }}
    .header h2 {{ color: #6366f1; margin: 0; font-size: 22px; }}
    .button {{ display: inline-block; padding: 12px 24px; background-color: #6366f1; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
    .footer {{ margin-top: 24px; border-top: 1px solid #27272a; padding-top: 16px; font-size: 12px; color: #71717a; text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2>📧 Email Verification Required</h2>
      <p style="color: #a1a1aa; font-size: 14px; margin-top: 4px;">Please verify your email address to start scheduling interviews.</p>
    </div>

    <p style="font-size: 15px;">Dear <strong>{safe_name}</strong>,</p>
    <p style="font-size: 14px; color: #d4d4d8;">Thank you for registering. Please click the button below to verify your email address:</p>

    <div style="text-align: center;">
      <a href="{verification_url}" class="button">Verify Email</a>
    </div>

    <p style="font-size: 14px; color: #a1a1aa;">If the button doesn't work, you can copy and paste the following link into your browser:</p>
    <p style="font-size: 12px; color: #38bdf8; word-break: break-all;">{verification_url}</p>
    <p style="font-size: 13px; color: #f87171;">Note: This verification link will expire in 24 hours.</p>

    <div class="footer">
      IntelliView AI Interview Platform &bull; Automated Notification
    </div>
  </div>
</body>
</html>
"""

        # Try to load verification template from the file
        try:
            template_path = os.path.join(
                os.path.dirname(__file__),
                "../notification-template-engine/templates/en/html/email_verification.html",
            )
            with open(template_path, encoding="utf-8") as f:
                loaded_html = f.read()
            html_body = loaded_html.replace("{{name}}", safe_name).replace(
                "{{link}}", verification_url
            )
            logger.info("Loaded email verification template from file successfully.")
        except Exception as e:
            logger.warning(
                f"Could not load verification template from file: {e}. Using inline fallback."
            )

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = candidate_email

        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            logger.info(
                f"Attempting to send verification email via SMTP to {candidate_email}"
            )
            if port == 465:
                with smtplib.SMTP_SSL(host=host, port=port, timeout=10) as server:
                    if self.settings.smtp_user and self.settings.smtp_password:
                        server.login(
                            self.settings.smtp_user, self.settings.smtp_password
                        )
                    server.send_message(message)
            else:
                with smtplib.SMTP(host=host, port=port, timeout=10) as server:
                    if self.settings.smtp_use_tls:
                        server.starttls()
                    if self.settings.smtp_user and self.settings.smtp_password:
                        server.login(
                            self.settings.smtp_user, self.settings.smtp_password
                        )
                    server.send_message(message)
            logger.info("Verification email successfully dispatched.")
            return True, "Verification email sent successfully"
        except Exception as e:
            error_msg = f"Failed to send verification email: {e!s}"
            logger.warning(error_msg)
            return False, error_msg


# Default instance
email_service = EmailService()
