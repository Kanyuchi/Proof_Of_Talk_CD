"""Email delivery for POT Matchmaker — powered by Resend.

All sends are fire-and-forget — failures are logged but never raise to callers.
The system works without email; email is an enhancement layer.
"""
import base64
import io
import logging

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _qr_image_url(data: str, size: int = 200) -> str:
    """Return a publicly hosted QR code image URL using quickchart.io API."""
    from urllib.parse import quote
    return f"https://quickchart.io/qr?text={quote(data)}&size={size}&margin=1"


def _send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str | None = None,
    attachments: list[dict] | None = None,
) -> bool:
    """Send an email via Resend. Returns True on success, False on failure."""
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — email skipped")
        return False

    payload: dict = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    if attachments:
        payload["attachments"] = attachments

    try:
        resp = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info("Email sent to %s via Resend (subject: %s)", to_email, subject[:50])
            return True
        else:
            logger.warning("Resend error %s for %s: %s", resp.status_code, to_email, resp.text[:200])
            return False
    except Exception as exc:
        logger.warning("Email send failed for %s: %s", to_email, exc)
        return False


def send_password_reset_email(
    to_email: str,
    user_name: str,
    reset_token: str,
    app_url: str | None = None,
) -> None:
    """Send a password reset email with a tokenized link.

    Args:
        to_email: Recipient email address.
        user_name: Full name of the user.
        reset_token: JWT reset token.
        app_url: Base URL of the app for the reset link.
    """
    return  # BLOCKED: platform not yet open to attendees

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = user_name.split()[0] if user_name else user_name
    reset_link = f"{app_url}/reset-password?token={reset_token}"

    subject = "Reset your Proof of Talk password"
    body_html = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d1a; color: #e8e8f0; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
  <div style="margin-bottom: 24px;">
    <div style="width: 28px; height: 36px; background: #E76315; clip-path: polygon(0 0, 100% 8%, 100% 92%, 0 100%); display: inline-block; vertical-align: middle; margin-right: 10px;"></div>
    <span style="font-size: 16px; font-weight: 600; vertical-align: middle; color: #fff;">Proof of Talk 2026</span>
  </div>

  <h1 style="font-size: 22px; font-weight: 700; color: #fff; margin: 0 0 8px;">Reset your password</h1>
  <p style="color: rgba(255,255,255,0.5); margin: 0 0 28px; font-size: 14px;">
    Hi {first_name}, we received a request to reset your password.
  </p>

  <a href="{reset_link}" style="display: block; background: #E76315; color: #fff; text-align: center; padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 14px; margin-bottom: 24px;">
    Reset my password &rarr;
  </a>

  <p style="font-size: 13px; color: rgba(255,255,255,0.4); margin: 0 0 8px;">
    This link expires in 15 minutes. If you didn&rsquo;t request this, you can safely ignore this email.
  </p>

  <p style="font-size: 11px; color: rgba(255,255,255,0.2); text-align: center; margin: 24px 0 0;">
    Proof of Talk &middot; Louvre Palace, Paris &middot; June 2&ndash;3, 2026
  </p>
</body>
</html>
"""
    body_text = (
        f"Reset your password\n\n"
        f"Hi {first_name},\n\n"
        f"We received a request to reset your password.\n\n"
        f"Reset your password: {reset_link}\n\n"
        f"This link expires in 15 minutes. If you didn't request this, ignore this email.\n\n"
        f"Proof of Talk · Louvre Palace, Paris · June 2–3, 2026"
    )

    _send_email(to_email, subject, body_html, body_text)


def send_match_intro_email(
    to_email: str,
    attendee_name: str,
    match_name: str,
    match_title: str,
    match_company: str,
    explanation: str,
    match_count: int,
    app_url: str | None = None,
    magic_token: str | None = None,
) -> None:
    """Send the 'we found your top match' email after pipeline completes.

    TEMPORARILY DISABLED — emails going out before platform is ready for
    attendees to sign in. Re-enable when registration flow is live.
    """
    return  # BLOCKED: attendees receiving emails but can't access platform yet

    """
    Args:
        to_email: Recipient email address.
        attendee_name: First name (or full name) of the recipient.
        match_name: Name of the top-ranked match.
        match_title: Title of the top-ranked match.
        match_company: Company of the top-ranked match.
        explanation: First 200 chars of the AI match explanation.
        match_count: Total number of matches generated.
        app_url: Base URL of the app for the CTA link.
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    short_explanation = explanation[:220] + "…" if len(explanation) > 220 else explanation
    dashboard_url = f"{app_url}/m/{magic_token}" if magic_token else f"{app_url}/matches"
    qr_url = _qr_image_url(dashboard_url) if magic_token else ""

    subject = f"Your Proof of Talk introductions are ready, {first_name}"
    body_html = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d1a; color: #e8e8f0; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
  <div style="margin-bottom: 24px;">
    <div style="width: 28px; height: 36px; background: #E76315; clip-path: polygon(0 0, 100% 8%, 100% 92%, 0 100%); display: inline-block; vertical-align: middle; margin-right: 10px;"></div>
    <span style="font-size: 16px; font-weight: 600; vertical-align: middle; color: #fff;">Proof of Talk 2026</span>
  </div>

  <h1 style="font-size: 22px; font-weight: 700; color: #fff; margin: 0 0 8px;">{first_name}, we found your connections at the Louvre</h1>
  <p style="color: rgba(255,255,255,0.5); margin: 0 0 28px; font-size: 14px;">
    Our Matchmaker has matched you with {match_count} attendee{'' if match_count == 1 else 's'} for Proof of Talk Paris, June 2–3.
  </p>

  <div style="background: rgba(231,99,21,0.08); border: 1px solid rgba(231,99,21,0.2); border-left: 3px solid #E76315; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <div style="font-size: 11px; color: #E76315; text-transform: uppercase; font-weight: 600; letter-spacing: 0.08em; margin-bottom: 12px;">Your #1 introduction</div>
    <div style="font-weight: 700; font-size: 16px; color: #fff;">{match_name}</div>
    <div style="font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: 12px;">{match_title} &middot; {match_company}</div>
    <p style="font-size: 13px; color: rgba(255,255,255,0.7); line-height: 1.6; margin: 0;">{short_explanation}</p>
  </div>

  <a href="{dashboard_url}" style="display: block; background: #E76315; color: #fff; text-align: center; padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 14px; margin-bottom: 16px;">
    View all your introductions →
  </a>

  {"" if not qr_url else '<div style="text-align: center; margin-bottom: 24px;"><p style="color: rgba(255,255,255,0.35); font-size: 11px; margin: 0 0 8px;">Or scan to open on your phone</p><img src="' + qr_url + '" width="140" height="140" alt="QR Code" style="border-radius: 8px; background: #fff; padding: 4px;" /></div>'}

  <p style="font-size: 11px; color: rgba(255,255,255,0.2); text-align: center; margin: 0;">
    Proof of Talk &middot; Louvre Palace, Paris &middot; June 2–3, 2026
  </p>
</body>
</html>
"""
    body_text = (
        f"Proof of Talk 2026 — Your introductions are ready\n\n"
        f"Hi {first_name},\n\n"
        f"We found {match_count} connection(s) for you at Proof of Talk Paris.\n\n"
        f"Your #1 introduction: {match_name}, {match_title} at {match_company}\n\n"
        f"{short_explanation}\n\n"
        f"View all: {dashboard_url}\n\n"
        f"Proof of Talk · Louvre Palace, Paris · June 2–3, 2026"
    )

    _send_email(to_email, subject, body_html, body_text)


def send_mutual_match_email(
    to_email: str,
    attendee_name: str,
    other_name: str,
    other_title: str,
    other_company: str,
    app_url: str | None = None,
) -> None:
    """Send a 'mutual match confirmed' notification email.

    Args:
        to_email: Recipient email.
        attendee_name: Name of the recipient.
        other_name: Name of the other party who accepted.
        other_title: Title of the other party.
        other_company: Company of the other party.
        app_url: Base URL of the app for the CTA link.
    """
    return  # BLOCKED: platform not yet open to attendees

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    other_first = other_name.split()[0] if other_name else other_name

    subject = f"You and {other_first} both want to meet — schedule your time in Paris"
    body_html = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d1a; color: #e8e8f0; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
  <div style="margin-bottom: 24px;">
    <div style="width: 28px; height: 36px; background: #E76315; clip-path: polygon(0 0, 100% 8%, 100% 92%, 0 100%); display: inline-block; vertical-align: middle; margin-right: 10px;"></div>
    <span style="font-size: 16px; font-weight: 600; vertical-align: middle; color: #fff;">Proof of Talk 2026</span>
  </div>

  <div style="background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.2); border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
    <div style="font-size: 28px; margin-bottom: 8px;">🤝</div>
    <h1 style="font-size: 20px; font-weight: 700; color: #34d399; margin: 0 0 4px;">Mutual match confirmed!</h1>
    <p style="font-size: 14px; color: rgba(255,255,255,0.5); margin: 0;">
      You and {other_name} both accepted each other.
    </p>
  </div>

  <p style="font-size: 14px; color: rgba(255,255,255,0.7); margin: 0 0 20px;">
    Hi {first_name}, <strong style="color: #fff;">{other_name}</strong> ({other_title} at {other_company}) accepted your connection request.
    Pick a time at POT 2026 — a quick 20-minute meeting at the Louvre could be the start of something significant.
  </p>

  <a href="{app_url}/matches" style="display: block; background: #34d399; color: #0d0d1a; text-align: center; padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 700; font-size: 14px; margin-bottom: 24px;">
    Schedule your meeting →
  </a>

  <p style="font-size: 11px; color: rgba(255,255,255,0.2); text-align: center; margin: 0;">
    Proof of Talk &middot; Louvre Palace, Paris &middot; June 2–3, 2026
  </p>
</body>
</html>
"""
    body_text = (
        f"Mutual match confirmed!\n\n"
        f"Hi {first_name},\n\n"
        f"{other_name} ({other_title} at {other_company}) also accepted the connection.\n"
        f"Schedule your meeting: {app_url}/matches\n\n"
        f"Proof of Talk · Louvre Palace, Paris · June 2–3, 2026"
    )

    _send_email(to_email, subject, body_html, body_text)


def send_meeting_confirmation_email(
    to_email: str,
    attendee_name: str,
    other_name: str,
    other_company: str,
    meeting_time_str: str,
    meeting_location: str,
    app_url: str | None = None,
) -> None:
    """Send a meeting confirmation email with time/location when a slot is booked.

    Args:
        to_email: Recipient email.
        attendee_name: Name of the recipient.
        other_name: Name of the meeting partner.
        other_company: Company of the meeting partner.
        meeting_time_str: Human-readable meeting time (already formatted).
        meeting_location: Meeting location string.
        app_url: Base URL of the app.
    """
    return  # BLOCKED: platform not yet open to attendees

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    other_first = other_name.split()[0] if other_name else other_name

    subject = f"Meeting confirmed: {first_name} & {other_first} · {meeting_time_str}"
    body_html = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d0d1a; color: #e8e8f0; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
  <div style="margin-bottom: 24px;">
    <div style="width: 28px; height: 36px; background: #E76315; clip-path: polygon(0 0, 100% 8%, 100% 92%, 0 100%); display: inline-block; vertical-align: middle; margin-right: 10px;"></div>
    <span style="font-size: 16px; font-weight: 600; vertical-align: middle; color: #fff;">Proof of Talk 2026</span>
  </div>

  <h1 style="font-size: 20px; font-weight: 700; color: #fff; margin: 0 0 20px;">📅 Your meeting is booked</h1>

  <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <div style="font-size: 13px; color: rgba(255,255,255,0.4); margin-bottom: 4px;">Meeting with</div>
    <div style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 16px;">{other_name} · {other_company}</div>
    <div style="display: flex; gap: 24px; flex-wrap: wrap;">
      <div>
        <div style="font-size: 11px; color: rgba(255,255,255,0.3); text-transform: uppercase; margin-bottom: 2px;">When</div>
        <div style="font-size: 14px; color: #34d399; font-weight: 600;">{meeting_time_str}</div>
      </div>
      <div>
        <div style="font-size: 11px; color: rgba(255,255,255,0.3); text-transform: uppercase; margin-bottom: 2px;">Where</div>
        <div style="font-size: 14px; color: rgba(255,255,255,0.7);">{meeting_location}</div>
      </div>
    </div>
  </div>

  <a href="{app_url}/matches" style="display: block; background: #E76315; color: #fff; text-align: center; padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Download calendar invite →
  </a>
  <p style="font-size: 12px; color: rgba(255,255,255,0.3); text-align: center; margin: 0 0 24px;">
    (Download .ics from the app to add to your calendar)
  </p>

  <p style="font-size: 11px; color: rgba(255,255,255,0.2); text-align: center; margin: 0;">
    Proof of Talk &middot; Louvre Palace, Paris &middot; June 2–3, 2026
  </p>
</body>
</html>
"""
    body_text = (
        f"Meeting confirmed: {attendee_name} & {other_name}\n\n"
        f"When: {meeting_time_str}\n"
        f"Where: {meeting_location}\n\n"
        f"View & download calendar invite: {app_url}/matches\n\n"
        f"Proof of Talk · Louvre Palace, Paris · June 2–3, 2026"
    )

    _send_email(to_email, subject, body_html, body_text)


# ── Post-event emails (Phase 6) ─────────────────────────────────────


def send_post_event_wrapup_email(
    to_email: str,
    attendee_name: str,
    total_matches: int,
    mutual_accepts: int,
    meetings_held: int,
    top_connections: list[dict],
    magic_token: str | None = None,
    app_url: str | None = None,
) -> None:
    """D+1 wrap-up email: summarises the attendee's POT 2026 experience.

    top_connections: list of dicts with keys name, company, title, linkedin_url.
    """
    return  # BLOCKED: platform not yet open to attendees


def send_followup_nudge_email(
    to_email: str,
    attendee_name: str,
    connections: list[dict],
    magic_token: str | None = None,
    app_url: str | None = None,
) -> None:
    """D+7 nudge email: reminds attendee to follow up on connections.

    connections: list of dicts with keys name, company, linkedin_url.
    """
    return  # BLOCKED: platform not yet open to attendees
