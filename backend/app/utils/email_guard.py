"""Outbound-email safety guard.

When settings.EMAIL_TEST_REDIRECT_TO is set, ALL outbound email is rerouted to
that single address and any cc/bcc is dropped — so testing flows can never reach
real recipients. Applied at every transmit chokepoint (EmailService Resend/SMTP
and resend_service).
"""
import logging
from typing import List, Optional, Tuple, Union

from app.core.config import settings

logger = logging.getLogger(__name__)


def _as_list(x: Union[None, str, List[str]]) -> List[str]:
    if not x:
        return []
    return list(x) if isinstance(x, (list, tuple)) else [x]


def redirect_recipients(
    to: Union[None, str, List[str]],
    cc: Union[None, str, List[str]] = None,
    bcc: Union[None, str, List[str]] = None,
) -> Tuple[List[str], List[str], List[str], bool, str]:
    """Return (to, cc, bcc, redirected, original_recipients_str).

    If EMAIL_TEST_REDIRECT_TO is set, `to` becomes [that address] and cc/bcc are
    emptied. Otherwise inputs pass through unchanged (normalized to lists).
    """
    to_l, cc_l, bcc_l = _as_list(to), _as_list(cc), _as_list(bcc)
    redirect = getattr(settings, "EMAIL_TEST_REDIRECT_TO", None)
    if not redirect:
        return to_l, cc_l, bcc_l, False, ""
    original = ", ".join(to_l + cc_l + bcc_l) or "(none)"
    logger.warning(
        "[EMAIL REDIRECT] EMAIL_TEST_REDIRECT_TO active — rerouting "
        f"to={to_l} cc={cc_l} bcc={bcc_l} -> {redirect}"
    )
    return [redirect], [], [], True, original


def tag_subject(subject: str, original: str) -> str:
    """Prefix the subject so the test inbox shows the intended recipient(s)."""
    return f"[TEST→ {original}] {subject}"
