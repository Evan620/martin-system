import os
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

from app.core.config import settings

# Try to import resend, fall back gracefully if not available
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


class EmailService:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
            
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Use EMAIL_FROM and EMAIL_FROM_NAME for Resend (verified domain)
        # Fall back to EMAILS_FROM_EMAIL for SMTP compatibility
        self.from_email = getattr(settings, 'EMAIL_FROM', settings.EMAILS_FROM_EMAIL)
        self.from_name = getattr(settings, 'EMAIL_FROM_NAME', settings.EMAILS_FROM_NAME)
        
        # Configure Resend if available
        if RESEND_AVAILABLE and settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY
            self.use_resend = True
        else:
            self.use_resend = False
            # SMTP fallback settings
            self.smtp_server = settings.SMTP_HOST
            self.smtp_port = settings.SMTP_PORT
            self.smtp_user = settings.SMTP_USER
            self.smtp_password = settings.SMTP_PASSWORD

    def _create_calendar_invite(
        self,
        title: str,
        description: str,
        start_time: datetime,
        duration_minutes: int,
        location: Optional[str] = None,
        attendees: List[str] = None
    ) -> bytes:
        """
        Creates an iCalendar (.ics) invite.
        """
        cal = Calendar()
        cal.add('prodid', '-//ECOWAS Summit TWG//martin-system//EN')
        cal.add('version', '2.0')
        cal.add('method', 'REQUEST')

        event = Event()
        event.add('summary', title)
        event.add('description', description)
        event.add('dtstart', start_time)
        event.add('dtend', start_time + timedelta(minutes=duration_minutes))
        event.add('dtstamp', datetime.now(pytz.utc))
        
        if location:
            event.add('location', location)

        if attendees:
            for email in attendees:
                event.add('attendee', f'MAILTO:{email}', parameters={'RSVP': 'TRUE'})

        cal.add_component(event)
        return cal.to_ical()

    async def send_meeting_invite(
        self,
        to_emails: List[str],
        subject: str,
        template_name: str,
        template_context: Dict[str, Any],
        meeting_details: Dict[str, Any],
        attachments: List[Dict[str, Any]] = None
    ):
        """
        Sends a meeting invitation with an ICS attachment.
        """
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**template_context)
        
        # Create ICS
        ics_content = self._create_calendar_invite(
            title=meeting_details['title'],
            description=meeting_details.get('description', ''),
            start_time=meeting_details['start_time'],
            duration_minutes=meeting_details.get('duration', 60),
            location=meeting_details.get('location'),
            attendees=to_emails
        )

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send to: {to_emails}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="invite.ics",
                extra_attachments=attachments
            )
        else:
            return await self._send_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="invite.ics",
                extra_attachments=attachments
            )

    async def send_meeting_update(
        self,
        to_emails: List[str],
        template_context: Dict[str, Any],
        meeting_details: Dict[str, Any],
        changes: List[str] = None
    ):
        """
        Sends a meeting update notification with an updated ICS attachment.
        """
        template = self.jinja_env.get_template("meeting_update.html")
        template_context["changes"] = changes or []
        html_content = template.render(**template_context)
        
        ics_content = self._create_calendar_invite(
            title=meeting_details['title'],
            description=meeting_details.get('description', ''),
            start_time=meeting_details['start_time'],
            duration_minutes=meeting_details.get('duration', 60),
            location=meeting_details.get('location'),
            attendees=to_emails
        )

        subject = f"UPDATED: {meeting_details['title']}"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send update to: {to_emails}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="meeting_update.ics"
            )
        else:
            return await self._send_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="meeting_update.ics"
            )

    async def send_meeting_reminder(
        self,
        to_emails: List[str],
        template_context: Dict[str, Any],
        meeting_details: Dict[str, Any]
    ):
        """
        Sends a meeting reminder email.
        """
        template = self.jinja_env.get_template("meeting_reminder.html")
        html_content = template.render(**template_context)
        
        ics_content = self._create_calendar_invite(
            title=meeting_details['title'],
            description=meeting_details.get('description', ''),
            start_time=meeting_details['start_time'],
            duration_minutes=meeting_details.get('duration', 60),
            location=meeting_details.get('location'),
            attendees=to_emails
        )

        subject = f"REMINDER: {meeting_details['title']}"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send reminder to: {to_emails}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="reminder.ics"
            )
        else:
            return await self._send_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="reminder.ics"
            )

    async def send_minutes_nudge(
        self,
        to_emails: List[str],
        template_context: Dict[str, Any]
    ):
        """
        Sends a nudge to upload minutes.
        """
        template = self.jinja_env.get_template("minutes_nudge.html")
        html_content = template.render(**template_context)
        
        subject = f"ACTION: Missing Minutes for {template_context.get('meeting_title', 'Meeting')}"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send nudge to: {to_emails}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content
            )
        else:
            return await self._send_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content
            )

    async def send_user_invite(
        self,
        to_email: str,
        full_name: str,
        password: str,
        role: str,
        login_url: str
    ):
        """
        Sends a user invitation email with temporary credentials.
        """
        template = self.jinja_env.get_template("user_invite.html")
        context = {
            "full_name": full_name,
            "password": password,
            "role": role.replace("_", " ").title(),
            "login_url": login_url
        }
        html_content = template.render(**context)
        subject = "Welcome to ECOWAS Summit TWG Support System"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send invite to: {to_email}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content
            )
        else:
            return await self._send_via_smtp(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content
            )



    async def send_minutes_published_email(
        self,
        to_emails: List[str],
        template_context: Dict[str, Any],
        pdf_content: bytes,
        pdf_filename: str = "Minutes.pdf"
    ):
        """
        Sends Minutes Published email with PDF attachment.
        """
        template = self.jinja_env.get_template("minutes_published.html")
        html_content = template.render(**template_context)
        
        subject = f"OFFICIAL MINUTES: {template_context.get('meeting_title')}"
        
        # Prepare attachment
        attachments = [{
            "filename": pdf_filename,
            "content": pdf_content,
            "content_type": "application/pdf"
        }]

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send Minutes to: {to_emails}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                extra_attachments=attachments
            )
        else:
            return await self._send_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                extra_attachments=attachments
            )

    def _create_cancel_invite(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        location: Optional[str] = None
    ) -> bytes:
        """
        Creates an iCalendar (.ics) cancellation notice.
        """
        cal = Calendar()
        cal.add('prodid', '-//ECOWAS Summit TWG//martin-system//EN')
        cal.add('version', '2.0')
        cal.add('method', 'CANCEL')

        event = Event()
        event.add('summary', f"CANCELLED: {title}")
        event.add('dtstart', start_time)
        event.add('dtend', start_time + timedelta(minutes=duration_minutes))
        event.add('dtstamp', datetime.now(pytz.utc))
        event.add('status', 'CANCELLED')
        
        if location:
            event.add('location', location)

        cal.add_component(event)
        return cal.to_ical()

    async def send_meeting_cancellation(
        self,
        to_emails: List[str],
        template_context: Dict[str, Any],
        meeting_details: Dict[str, Any],
        reason: str = None
    ):
        """
        Sends a meeting cancellation notification with a CANCEL ICS attachment.
        """
        template = self.jinja_env.get_template("meeting_cancellation.html")
        template_context["reason"] = reason
        html_content = template.render(**template_context)
        
        ics_content = self._create_cancel_invite(
            title=meeting_details['title'],
            start_time=meeting_details['start_time'],
            duration_minutes=meeting_details.get('duration', 60),
            location=meeting_details.get('location')
        )

        subject = f"CANCELLED: {meeting_details['title']}"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send cancellation to: {to_emails}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="cancellation.ics"
            )
        else:
            return await self._send_via_smtp(
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                ics_content=ics_content,
                ics_filename="cancellation.ics"
            )

    async def _send_via_resend(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        ics_content: bytes = None,
        ics_filename: str = "invite.ics",
        extra_attachments: List[Dict[str, Any]] = None
    ) -> bool:
        """
        Send email using Resend API (works on Railway).
        """
        import base64
        
        attachments = []
        if ics_content:
            attachments.append({
                "filename": ics_filename,
                "content": base64.b64encode(ics_content).decode('utf-8'),
                "content_type": "text/calendar"
            })
            
        if extra_attachments:
            for attachment in extra_attachments:
                # Expects: filename, content (bytes), content_type
                attachments.append({
                    "filename": attachment["filename"],
                    "content": base64.b64encode(attachment["content"]).decode('utf-8'),
                    "content_type": attachment["content_type"]
                })

        params = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": to_emails,
            "subject": subject,
            "html": html_content,
        }
        
        if attachments:
            params["attachments"] = attachments
            
        print(f"[Resend Debug] ICS Content: {bool(ics_content)}")
        if ics_content:
            # Add ICS as a specially formatted attachment
            # Resend might not support 'content_type' with parameters perfectly in all SDK versions,
            # but usually passing the full string works or is handled by the provider.
            # Key modification: Explicitly set method=REQUEST
            params["attachments"] = params.get("attachments", []) + [{
                "filename": ics_filename,
                "content": base64.b64encode(ics_content).decode('utf-8'),
                "content_type": "text/calendar; method=REQUEST"
            }]
            
        # Debug logging
        print(f"[Resend] Sending email to {len(to_emails)} recipients. Subject: {subject}")
        print(f"[Resend] Has attachments: {bool(attachments)} Count: {len(attachments) if attachments else 0}")

        try:
            result = resend.Emails.send(params)
            print(f"[Resend] Email sent successfully: {result}")
            return True
        except Exception as e:
            print(f"[Resend] Failed to send email: {e}")
            raise

    async def _send_via_smtp(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        ics_content: bytes = None,
        ics_filename: str = "invite.ics",
        extra_attachments: List[Dict[str, Any]] = None
    ) -> bool:
        """
        Send email using SMTP (fallback, may not work on some cloud platforms).
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        message = MIMEMultipart("mixed")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = ", ".join(to_emails)

        part_html = MIMEText(html_content, "html")
        message.attach(part_html)

        if ics_content:
            part_ics = MIMEBase("text", "calendar", method="REQUEST")
            part_ics.set_payload(ics_content)
            encoders.encode_base64(part_ics)
            part_ics.add_header("Content-Disposition", "attachment", filename=ics_filename)
            part_ics.add_header("Content-Type", "text/calendar; method=REQUEST")
            part_ics.add_header("Content-Class", "urn:content-classes:calendarmessage")
            part_ics.add_header("Content-Class", "urn:content-classes:calendarmessage")
            message.attach(part_ics)

        if extra_attachments:
            for attachment in extra_attachments:
                # Expects: filename, content (bytes), content_type
                main_type, sub_type = attachment["content_type"].split("/", 1)
                part = MIMEBase(main_type, sub_type)
                part.set_payload(attachment["content"])
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment["filename"],
                )
                message.attach(part)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, to_emails, message.as_string())
        
        return True

    async def send_password_reset_email(
        self,
        to_email: str,
        full_name: str,
        reset_token: str,
        reset_url_base: str
    ):
        """
        Sends a password reset email with a secure reset link.
        """
        template = self.jinja_env.get_template("password_reset.html")
        reset_url = f"{reset_url_base}?token={reset_token}"
        context = {
            "full_name": full_name,
            "reset_url": reset_url
        }
        html_content = template.render(**context)
        subject = "Password Reset Request - ECOWAS Summit TWG"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send password reset to: {to_email}")
            print(f"[EmailService] Reset URL: {reset_url}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content
            )
        else:
            return await self._send_via_smtp(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content
            )

    async def send_organization_invitation(
        self,
        to_email: str,
        organization_name: str,
        twg_name: str,
        inviter_name: str,
        invitation_id: str,
        expires_at: datetime,
        custom_message: Optional[str] = None
    ):
        """
        Sends an organization invitation email with accept/decline buttons.
        """
        template = self.jinja_env.get_template("organization_invitation.html")

        # Build response URLs
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        accept_url = f"{base_url}/invitations/{invitation_id}/respond?action=accept"
        decline_url = f"{base_url}/invitations/{invitation_id}/respond?action=decline"

        context = {
            "organization_name": organization_name,
            "twg_name": twg_name,
            "inviter_name": inviter_name,
            "custom_message": custom_message,
            "accept_url": accept_url,
            "decline_url": decline_url,
            "expires_at": expires_at.strftime("%B %d, %Y")
        }
        html_content = template.render(**context)
        subject = f"Invitation to Join {twg_name} - ECOWAS Summit TWG"

        if not settings.EMAILS_ENABLED:
            print(f"[EmailService] Emails disabled. Would send org invitation to: {to_email}")
            print(f"[EmailService] Accept URL: {accept_url}")
            return True

        if self.use_resend:
            return await self._send_via_resend(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content
            )
        else:
            return await self._send_via_smtp(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content
            )


email_service = EmailService()
