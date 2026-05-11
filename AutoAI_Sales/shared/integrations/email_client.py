from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


class EmailClient:
    def __init__(self):
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.email_notifications_enabled
            and self.settings.smtp_host
            and self.settings.smtp_port
            and self.settings.smtp_username
            and self.settings.smtp_password
            and self.settings.email_from
        )

    def send_test_email(self, to_email: str, subject: str = "Halcyon SMTP Test") -> bool:
        html = """
        <html>
          <body>
            <h3>SMTP test successful</h3>
            <p>Your Halcyon Auto SMTP integration is working.</p>
          </body>
        </html>
        """
        text = "SMTP test successful. Your Halcyon Auto SMTP integration is working."
        message = self.build_email_message(
            to_email=to_email,
            subject=subject,
            text_body=text,
            html_body=html,
        )
        return self.send_message(message, raise_on_error=True)

    def send_appointment_confirmation(self, lead, appointment) -> bool:
        recipient = getattr(lead, "email", None)
        if not recipient:
            logger.warning(
                "Appointment confirmation skipped for %s because lead email is missing.",
                getattr(appointment, "public_id", "unknown"),
            )
            return False

        full_name = self._full_name(lead)
        start_label = self._format_datetime(appointment.start_time)
        end_label = self._format_datetime(appointment.end_time)
        dealership_label = getattr(appointment, "dealership_id", self.settings.default_dealership_id)
        sales_url = self.settings.public_sales_url

        subject = (
            f"{self.settings.appointment_email_subject_prefix}: "
            f"Appointment Confirmed ({appointment.public_id})"
        )

        text_body = (
            f"Hello {full_name or 'there'},\n\n"
            "Your dealership appointment has been confirmed.\n\n"
            f"Appointment ID: {appointment.public_id}\n"
            f"Dealership: {dealership_label}\n"
            f"Vehicle: {appointment.vehicle_id}\n"
            f"Representative: {appointment.rep_id}\n"
            f"Start: {start_label}\n"
            f"End: {end_label}\n"
            f"Status: {appointment.status}\n"
            f"Channel: {appointment.channel}\n\n"
            f"If you need to reschedule, please reply to this email or visit {sales_url}\n\n"
            "Thank you,\n"
            "Halcyon Auto Sales"
        )

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #1f2937;">
            <p>Hello {full_name or 'there'},</p>
            <p>Your dealership appointment has been confirmed.</p>
            <table cellpadding="6" cellspacing="0" border="0">
              <tr><td><strong>Appointment ID</strong></td><td>{appointment.public_id}</td></tr>
              <tr><td><strong>Dealership</strong></td><td>{dealership_label}</td></tr>
              <tr><td><strong>Vehicle</strong></td><td>{appointment.vehicle_id}</td></tr>
              <tr><td><strong>Representative</strong></td><td>{appointment.rep_id}</td></tr>
              <tr><td><strong>Start</strong></td><td>{start_label}</td></tr>
              <tr><td><strong>End</strong></td><td>{end_label}</td></tr>
              <tr><td><strong>Status</strong></td><td>{appointment.status}</td></tr>
              <tr><td><strong>Channel</strong></td><td>{appointment.channel}</td></tr>
            </table>
            <p>
              If you need to reschedule, please reply to this email or visit
              <a href="{sales_url}">{sales_url}</a>.
            </p>
            <p>Thank you,<br/>Halcyon Auto Sales</p>
          </body>
        </html>
        """

        message = self.build_email_message(
            to_email=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return self.send_message(message)

    def send_appointment_reminder(self, lead, appointment, reminder_type: str) -> bool:
        recipient = getattr(lead, "email", None)
        if not recipient:
            logger.warning(
                "Appointment reminder skipped for %s because lead email is missing.",
                getattr(appointment, "public_id", "unknown"),
            )
            return False

        full_name = self._full_name(lead)
        start_label = self._format_datetime(appointment.start_time)
        dealership_label = getattr(appointment, "dealership_id", self.settings.default_dealership_id)
        sales_url = self.settings.public_sales_url

        subject = (
            f"{self.settings.appointment_email_subject_prefix}: "
            f"Appointment Reminder ({reminder_type}) - {appointment.public_id}"
        )

        text_body = (
            f"Hello {full_name or 'there'},\n\n"
            f"This is a reminder for your upcoming dealership appointment.\n\n"
            f"Reminder: {reminder_type}\n"
            f"Appointment ID: {appointment.public_id}\n"
            f"Dealership: {dealership_label}\n"
            f"Vehicle: {appointment.vehicle_id}\n"
            f"Representative: {appointment.rep_id}\n"
            f"Start: {start_label}\n\n"
            f"If you need to reschedule, please reply to this email or visit {sales_url}\n\n"
            "Thank you,\n"
            "Halcyon Auto Sales"
        )

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #1f2937;">
            <p>Hello {full_name or 'there'},</p>
            <p>This is a reminder for your upcoming dealership appointment.</p>
            <table cellpadding="6" cellspacing="0" border="0">
              <tr><td><strong>Reminder</strong></td><td>{reminder_type}</td></tr>
              <tr><td><strong>Appointment ID</strong></td><td>{appointment.public_id}</td></tr>
              <tr><td><strong>Dealership</strong></td><td>{dealership_label}</td></tr>
              <tr><td><strong>Vehicle</strong></td><td>{appointment.vehicle_id}</td></tr>
              <tr><td><strong>Representative</strong></td><td>{appointment.rep_id}</td></tr>
              <tr><td><strong>Start</strong></td><td>{start_label}</td></tr>
            </table>
            <p>
              If you need to reschedule, please reply to this email or visit
              <a href="{sales_url}">{sales_url}</a>.
            </p>
            <p>Thank you,<br/>Halcyon Auto Sales</p>
          </body>
        </html>
        """

        message = self.build_email_message(
            to_email=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return self.send_message(message)

    def send_nurture_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> bool:
        message = self.build_email_message(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return self.send_message(message)

    def build_email_message(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr(
            (self.settings.email_from_name, self.settings.email_from or self.settings.smtp_username or "")
        )
        message["To"] = to_email
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=None)
        if self.settings.email_reply_to:
            message["Reply-To"] = self.settings.email_reply_to

        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")
        return message

    def send_message(self, message: EmailMessage, *, raise_on_error: bool = False) -> bool:
        if not self.is_configured():
            logger.warning("SMTP email skipped because SMTP is not fully configured.")
            if raise_on_error:
                raise EmailDeliveryError("SMTP is not fully configured.")
            return False

        try:
            if self.settings.smtp_use_ssl:
                with smtplib.SMTP_SSL(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=self.settings.smtp_timeout_seconds,
                    context=ssl.create_default_context(),
                ) as server:
                    self._login(server)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=self.settings.smtp_timeout_seconds,
                ) as server:
                    server.ehlo()
                    if self.settings.smtp_use_tls:
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                    self._login(server)
                    server.send_message(message)

            logger.info("Email sent successfully to %s with subject %s", message.get("To"), message.get("Subject"))
            return True

        except Exception as exc:
            logger.exception("SMTP send failed for %s: %s", message.get("To"), exc)
            if raise_on_error:
                raise EmailDeliveryError(str(exc)) from exc
            return False

    def _login(self, server: smtplib.SMTP) -> None:
        server.login(self.settings.smtp_username, self.settings.smtp_password)

    @staticmethod
    def _full_name(lead) -> str:
        first = getattr(lead, "first_name", "") or ""
        last = getattr(lead, "last_name", "") or ""
        return f"{first.strip()} {last.strip()}".strip()

    @staticmethod
    def _format_datetime(value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %I:%M %p")
        except Exception:
            return value