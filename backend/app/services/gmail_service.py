"""
Gmail Service Layer

Provides Gmail API integration for sending and retrieving emails.
Follows singleton pattern similar to llm_service.py and redis_memory.py.
"""

import os
import base64
import logging
from typing import List, Dict, Any, Optional, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://mail.google.com/']


class GmailService:
    """Gmail service for sending and retrieving emails."""

    def __init__(
        self,
        credentials_file: str = "./credentials/gmail_credentials.json",
        token_file: str = "./credentials/gmail_token.json"
    ):
        """
        Initialize Gmail service with OAuth credentials.

        Args:
            credentials_file: Path to OAuth credentials JSON file
            token_file: Path to token storage file
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.credentials = self._get_credentials()
        self.service = self._build_service()
        logger.info("Gmail service initialized successfully")

    def _get_credentials(self) -> Credentials:
        """
        Get or refresh Gmail OAuth credentials.

        Returns:
            Valid Gmail API credentials
        """
        creds = None

        # Check if token file exists
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # If credentials are invalid or don't exist, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail credentials")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow for Gmail credentials")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                # Use fixed port 8080 for consistent redirect URI
                # Make sure to add http://localhost:8080/ to authorized redirect URIs in Google Cloud Console
                creds = flow.run_local_server(port=8080)

            # Save credentials for next time
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                logger.info(f"Credentials saved to {self.token_file}")

        return creds

    def _build_service(self) -> Resource:
        """
        Build Gmail API service.

        Returns:
            Gmail API service resource
        """
        from googleapiclient.discovery import build
        return build('gmail', 'v1', credentials=self.credentials)

    def send_message(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email message.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            cc: Optional CC recipient(s)
            bcc: Optional BCC recipient(s)
            attachments: Optional list of file paths to attach

        Returns:
            Dictionary with message ID and status
        """
        try:
            # Create message
            message = self._create_message(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc,
                attachments=attachments
            )

            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            logger.info(f"Email sent successfully. Message ID: {sent_message['id']}")
            return {
                'message_id': sent_message['id'],
                'thread_id': sent_message.get('threadId'),
                'label_ids': sent_message.get('labelIds', [])
            }

        except HttpError as error:
            logger.error(f"Gmail API error while sending email: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error while sending email: {error}")
            raise

    def _create_message(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Create a message for sending.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            cc: Optional CC recipient(s)
            bcc: Optional BCC recipient(s)
            attachments: Optional list of file paths to attach

        Returns:
            Dictionary with raw base64 encoded message
        """
        # Convert single recipients to lists
        to_list = [to] if isinstance(to, str) else to
        cc_list = [cc] if isinstance(cc, str) and cc else (cc or [])
        bcc_list = [bcc] if isinstance(bcc, str) and bcc else (bcc or [])

        # Create multipart message if HTML or attachments
        if html_body or attachments:
            message = MIMEMultipart('alternative' if html_body and not attachments else 'mixed')
        else:
            message = MIMEText(body)

        # Set headers
        message['to'] = ', '.join(to_list)
        message['subject'] = subject
        if cc_list:
            message['cc'] = ', '.join(cc_list)
        if bcc_list:
            message['bcc'] = ', '.join(bcc_list)

        # Add body parts for multipart messages
        if html_body or attachments:
            if html_body:
                # Create alternative container for text and HTML
                text_part = MIMEText(body, 'plain')
                html_part = MIMEText(html_body, 'html')
                message.attach(text_part)
                message.attach(html_part)
            else:
                # Just plain text
                text_part = MIMEText(body, 'plain')
                message.attach(text_part)

            # Add attachments
            if attachments:
                for file_path in attachments:
                    self._attach_file(message, file_path)

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    def _attach_file(self, message: MIMEMultipart, file_path: str) -> None:
        """
        Attach a file to an email message.

        Args:
            message: The MIME message to attach to
            file_path: Path to the file to attach
        """
        try:
            with open(file_path, 'rb') as file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(file_path)}'
            )
            message.attach(part)
            logger.debug(f"Attached file: {file_path}")

        except Exception as error:
            logger.error(f"Error attaching file {file_path}: {error}")
            raise

    def create_draft(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an email draft.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body

        Returns:
            Dictionary with draft ID and message info
        """
        try:
            # Create message
            message = self._create_message(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body
            )

            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()

            logger.info(f"Draft created successfully. Draft ID: {draft['id']}")
            return {
                'draft_id': draft['id'],
                'message_id': draft['message']['id']
            }

        except HttpError as error:
            logger.error(f"Gmail API error while creating draft: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error while creating draft: {error}")
            raise

    def search_messages(
        self,
        query: str,
        max_results: int = 10,
        include_spam_trash: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for messages matching a query.

        Args:
            query: Gmail search query (e.g., 'from:user@example.com is:unread')
            max_results: Maximum number of results to return
            include_spam_trash: Whether to include spam and trash

        Returns:
            List of message metadata dictionaries
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results,
                includeSpamTrash=include_spam_trash
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages matching query: {query}")

            return messages

        except HttpError as error:
            logger.error(f"Gmail API error while searching messages: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error while searching messages: {error}")
            raise

    def get_message(
        self,
        message_id: str,
        format: str = 'full'
    ) -> Dict[str, Any]:
        """
        Get a specific message by ID.

        Args:
            message_id: The message ID to retrieve
            format: Format of the message ('minimal', 'full', 'raw', 'metadata')

        Returns:
            Message data dictionary
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()

            logger.info(f"Retrieved message: {message_id}")
            return message

        except HttpError as error:
            logger.error(f"Gmail API error while getting message: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error while getting message: {error}")
            raise

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Get an email thread by ID.

        Args:
            thread_id: The thread ID to retrieve

        Returns:
            Thread data dictionary with all messages
        """
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()

            logger.info(f"Retrieved thread: {thread_id} with {len(thread.get('messages', []))} messages")
            return thread

        except HttpError as error:
            logger.error(f"Gmail API error while getting thread: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error while getting thread: {error}")
            raise

    def list_messages(
        self,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None,
        include_spam_trash: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List messages with optional label filters.

        Args:
            max_results: Maximum number of messages to return
            label_ids: Optional list of label IDs to filter by
            include_spam_trash: Whether to include spam and trash

        Returns:
            List of message metadata dictionaries
        """
        try:
            kwargs = {
                'userId': 'me',
                'maxResults': max_results,
                'includeSpamTrash': include_spam_trash
            }

            if label_ids:
                kwargs['labelIds'] = label_ids

            results = self.service.users().messages().list(**kwargs).execute()

            messages = results.get('messages', [])
            logger.info(f"Listed {len(messages)} messages")

            return messages

        except HttpError as error:
            logger.error(f"Gmail API error while listing messages: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error while listing messages: {error}")
            raise


# Singleton instance
_gmail_service: Optional[GmailService] = None


def get_gmail_service(
    credentials_file: str = "./credentials/gmail_credentials.json",
    token_file: str = "./credentials/gmail_token.json"
) -> GmailService:
    """
    Get or create Gmail service singleton.

    Args:
        credentials_file: Path to OAuth credentials JSON file
        token_file: Path to token storage file

    Returns:
        Gmail service instance
    """
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService(
            credentials_file=credentials_file,
            token_file=token_file
        )
    return _gmail_service
