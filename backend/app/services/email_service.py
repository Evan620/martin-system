import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

from app.core.config import settings

class EmailService:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
            
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.from_name = settings.EMAILS_FROM_NAME

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
        meeting_details: Dict[str, Any]
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

        # Build Email
        message = MIMEMultipart("mixed")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = ", ".join(to_emails)

        # Attachment: Content
        part_html = MIMEText(html_content, "html")
        message.attach(part_html)

        # Attachment: ICS
        part_ics = MIMEBase("text", "calendar", method="REQUEST")
        part_ics.set_payload(ics_content)
        encoders.encode_base64(part_ics)
        part_ics.add_header("Content-Disposition", "attachment", filename="invite.ics")
        part_ics.add_header("Content-Class", "urn:content-classes:calendarmessage")
        message.attach(part_ics)

        # Send
        if settings.EMAILS_ENABLED:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_emails, message.as_string())
        
        return True

email_service = EmailService()
