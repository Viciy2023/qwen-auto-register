"""Variable providers for email, username, password."""

from .one_sec_mail_provider import (
    MailTmProvider,
    OneSecMailProvider,
    get_email_provider,
)
from .username_provider import UsernameProvider

__all__ = [
    "MailTmProvider",
    "OneSecMailProvider",
    "UsernameProvider",
    "get_email_provider",
]
