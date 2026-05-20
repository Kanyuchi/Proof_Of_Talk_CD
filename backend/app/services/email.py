"""Email delivery for POT Matchmaker — powered by Resend.

All sends are fire-and-forget — failures are logged but never raise to callers.
The system works without email; email is an enhancement layer.
"""
import base64
import io
import logging
import os

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"

# Hosted email assets (served by the frontend at meet.proofoftalk.io/email/*).
# Override base via env in non-prod previews.
EMAIL_ASSET_BASE = os.getenv("EMAIL_ASSET_BASE", "https://meet.proofoftalk.io/email")
EMAIL_APP_URL = "https://meet.proofoftalk.io"
# Social links (clean base URLs — the ConvertKit ck_subscriber_id/utm params
# are per-recipient tracking and must NOT be hardcoded here).
EMAIL_LINKEDIN_URL = "https://www.linkedin.com/company/proofoftalk2026/"
EMAIL_X_URL = "https://x.com/proofoftalk"


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
    """Send an email via Resend. Returns True on success, False on failure.

    Central gate for ALL outbound mail. EMAIL_MODE controls who actually
    receives:
      off       — nothing sends (safe default)
      allowlist — only addresses in EMAIL_ALLOWLIST (team testing)
      all       — everyone
    This replaced the per-function `return # BLOCKED` guards so gating
    lives in exactly one place and rollout is a config change, not a code
    change.
    """
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — email skipped")
        return False

    mode = (settings.EMAIL_MODE or "off").strip().lower()
    if mode == "off":
        logger.info("EMAIL_MODE=off — skipped send to %s (subject: %s)", to_email, subject[:50])
        return False
    if mode == "allowlist":
        entries = [e.strip().lower() for e in (settings.EMAIL_ALLOWLIST or "").split(",") if e.strip()]
        # Entries starting with "@" match a whole domain (e.g. "@proofoftalk.io"
        # covers every team member, current and future); other entries are
        # exact addresses. Domain matching is preferred for the team list so
        # the env var doesn't need editing as people join.
        domains = {e[1:] for e in entries if e.startswith("@")}
        exacts = {e for e in entries if not e.startswith("@")}
        to_norm = to_email.strip().lower()
        to_domain = to_norm.rsplit("@", 1)[-1] if "@" in to_norm else ""
        if to_norm not in exacts and to_domain not in domains:
            logger.info(
                "EMAIL_MODE=allowlist — %s not in allowlist, skipped (subject: %s)",
                to_email, subject[:50],
            )
            return False
    # mode == "all" (or anything else falls through to send only if it
    # passed the explicit checks above) — for safety, treat unknown modes
    # as "off".
    if mode not in ("allowlist", "all"):
        logger.warning("EMAIL_MODE=%r unrecognised — treating as off, skipped %s", mode, to_email)
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


def _render_email(
    *,
    preheader: str,
    eyebrow: str,
    heading: str,
    body_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    footer_note: str | None = None,
    unsubscribe: bool = False,
    accent: str = "#C2632A",
) -> str:
    """Shared branded email shell, matching the Proof of Talk newsletter:
    Louvre header banner -> cream body (orange eyebrow, serif heading, sans
    body, terracotta CTA) -> serif date + stats footer -> Louvre footer
    banner -> social icons. Web-safe (table layout, inline styles, no web
    fonts) so Gmail/Outlook render it consistently.

    Args:
        preheader: hidden inbox-preview text.
        eyebrow: small uppercase label above the heading.
        heading: serif H1.
        body_html: main content as <tr><td>...</td></tr> rows.
        cta_label/cta_url: optional primary button.
        footer_note: small print directly under the body (e.g. expiry note).
        unsubscribe: show "Unsubscribe / Preferences" (marketing emails only;
            omit on transactional/security mail like password resets).
        accent: eyebrow + button colour (terracotta, matching the newsletter).
    """
    cream = "#F6F4EF"
    ink = "#211500"  # brand dark (Media Kit)
    body_color = "#3A3A3A"
    muted = "#7A7268"
    hairline = "#E0D6C8"
    # Brand fonts (Media Kit): Titles=Playfair Display, Body=Poppins. Embedded
    # via the <link> below — renders in Apple Mail; Gmail/Outlook strip web
    # fonts and fall back to the web-safe stack, which is the email ceiling.
    serif = "'Playfair Display', Georgia, 'Times New Roman', serif"
    sans = "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <tr><td style="padding: 12px 0 8px;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
            <td align="center" bgcolor="{accent}" style="border-radius: 4px;">
              <a href="{cta_url}" style="display: inline-block; padding: 15px 32px; font-family: {sans}; font-size: 13px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #ffffff; text-decoration: none; border-radius: 4px;">{cta_label} &rarr;</a>
            </td>
          </tr></table>
        </td></tr>"""

    footer_note_block = ""
    if footer_note:
        footer_note_block = f"""
        <tr><td style="padding: 14px 0 0; font-family: {sans}; font-size: 13px; line-height: 1.6; color: {muted};">{footer_note}</td></tr>"""

    unsub_block = ""
    if unsubscribe:
        unsub_block = f"""
            <tr><td align="center" style="padding: 14px 0 0; font-family:{sans}; font-size:12px; color:{muted};">
              <a href="{EMAIL_APP_URL}/unsubscribe" style="color:{muted}; text-decoration:underline;">Unsubscribe</a> &middot; <a href="{EMAIL_APP_URL}/profile" style="color:{muted}; text-decoration:underline;">Preferences</a>
            </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Poppins:wght@300;400;500;600&display=swap" rel="stylesheet"></head>
<body style="margin:0; padding:0; background:{cream};">
  <div style="display:none; max-height:0; overflow:hidden; opacity:0; color:{cream};">{preheader}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{cream};">
    <tr><td align="center" style="padding: 24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px; max-width:100%; background:{cream};">
        <!-- header banner -->
        <tr><td style="padding:0;">
          <a href="https://meet.proofoftalk.io"><img src="{EMAIL_ASSET_BASE}/header-banner.png" width="600" alt="Proof of Talk 2026, The Louvre Palace, 2 and 3 June" style="display:block; width:100%; max-width:600px; height:auto; border:0;" /></a>
        </td></tr>
        <!-- body -->
        <tr><td style="padding: 34px 44px 0;">
          <div style="font-family:{sans}; font-size:11px; font-weight:700; letter-spacing:0.16em; text-transform:uppercase; color:{accent}; margin-bottom:14px;">{eyebrow}</div>
          <h1 style="margin:0 0 18px; font-family:{serif}; font-size:28px; line-height:1.25; font-weight:600; color:{ink};">{heading}</h1>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="font-family:{sans}; font-size:16px; line-height:1.65; color:{body_color};">
            {body_html}
            {cta_block}
            {footer_note_block}
          </table>
        </td></tr>
        <!-- date + stats footer -->
        <tr><td style="padding: 34px 44px 28px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td align="center" style="padding-bottom:18px;"><div style="width:120px; height:1px; background:{accent}; opacity:0.5; margin:0 auto;"></div></td></tr>
            <tr><td align="center" style="font-family:{serif}; font-size:18px; font-weight:700; color:{ink};">June 2 &amp; 3, 2026</td></tr>
            <tr><td align="center" style="padding-top:4px; font-family:{sans}; font-size:14px; color:{muted};">The Louvre, Paris</td></tr>
            <tr><td align="center" style="padding:16px 0 0; font-family:{sans}; font-size:12px; letter-spacing:0.02em; color:{muted};">2,500 Leaders &middot; 85% Decision-Makers &middot; $18T AUM</td></tr>
          </table>
        </td></tr>
        <!-- footer banner -->
        <tr><td style="padding:0;">
          <a href="https://meet.proofoftalk.io"><img src="{EMAIL_ASSET_BASE}/footer-banner.png" width="600" alt="The room where you don't have to explain. Your work already did. Proof of Talk" style="display:block; width:100%; max-width:600px; height:auto; border:0;" /></a>
        </td></tr>
        <!-- social + unsubscribe -->
        <tr><td style="padding: 20px 44px 8px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td align="center">
              <a href="{EMAIL_LINKEDIN_URL}" style="text-decoration:none;"><img src="{EMAIL_ASSET_BASE}/icon-linkedin.png" width="28" height="28" alt="LinkedIn" style="border:0; display:inline-block; margin:0 5px; vertical-align:middle;" /></a>
              <a href="{EMAIL_X_URL}" style="text-decoration:none;"><img src="{EMAIL_ASSET_BASE}/icon-x.png" width="28" height="28" alt="X" style="border:0; display:inline-block; margin:0 5px; vertical-align:middle;" /></a>
            </td></tr>
            {unsub_block}
          </table>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


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

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = user_name.split()[0] if user_name else user_name
    reset_link = f"{app_url}/reset-password?token={reset_token}"

    subject = "Reset your Proof of Talk password"
    body_html = _render_email(
        preheader="Reset your Proof of Talk password. Link expires in 15 minutes.",
        eyebrow="Account",
        heading="Reset your password",
        body_html=f"""
            <tr><td style="padding: 0 0 4px;">Hi {first_name}, we received a request to reset the password on your Proof of Talk account. Tap below to choose a new one.</td></tr>
        """,
        cta_label="Reset my password",
        cta_url=reset_link,
        footer_note="This link expires in 15 minutes. If you didn&rsquo;t request this, you can safely ignore this email. Your password won&rsquo;t change.",
        unsubscribe=False,
    )
    body_text = (
        f"Reset your password\n\n"
        f"Hi {first_name},\n\n"
        f"We received a request to reset your password.\n\n"
        f"Reset your password: {reset_link}\n\n"
        f"This link expires in 15 minutes. If you didn't request this, ignore this email.\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
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

    subject = f"Your introductions for Proof of Talk 2026 are ready, {first_name}"
    body_html = _render_email(
        preheader=f"We found your {match_count} most valuable connections at the Louvre.",
        eyebrow="Your introductions",
        heading=f"{first_name}, your connections at the Louvre",
        body_html=(
            f"<tr><td style=\"padding:0 0 16px;\">Our Matchmaker has matched you with {match_count} attendee{'' if match_count == 1 else 's'} for Proof of Talk in Paris, ranked by who is most worth your time.</td></tr>"
            f"<tr><td style=\"padding:0 0 8px;\">"
            f"  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background:#FBF8F3; border-left:3px solid #C2632A;\">"
            f"    <tr><td style=\"padding:18px 20px;\">"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#C2632A; margin-bottom:8px;\">Your #1 introduction</div>"
            f"      <div style=\"font-family:Georgia,'Playfair Display',serif; font-size:18px; color:#211500; font-weight:600;\">{match_name}</div>"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:13px; color:#7A7268; margin-bottom:10px;\">{match_title}, {match_company}</div>"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:14px; line-height:1.6; color:#3A3A3A;\">{short_explanation}</div>"
            f"    </td></tr>"
            f"  </table>"
            f"</td></tr>"
        ),
        cta_label="View all your introductions",
        cta_url=dashboard_url,
        unsubscribe=True,
    )
    body_text = (
        f"Your introductions for Proof of Talk 2026 are ready, {first_name}\n\n"
        f"We found {match_count} connection(s) for you at Proof of Talk Paris.\n\n"
        f"Your #1 introduction: {match_name}, {match_title} at {match_company}\n\n"
        f"{short_explanation}\n\n"
        f"View all: {dashboard_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
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

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    other_first = other_name.split()[0] if other_name else other_name

    subject = f"You and {other_first} both want to meet at Proof of Talk"
    body_html = _render_email(
        preheader=f"{other_name} accepted your connection. Pick a time to meet in Paris.",
        eyebrow="Mutual match",
        heading=f"You are connected with {other_first}",
        body_html=(
            f"<tr><td style=\"padding:0 0 14px;\"><strong style=\"color:#211500;\">{other_name}</strong> ({other_title} at {other_company}) accepted your connection request.</td></tr>"
            f"<tr><td style=\"padding:0 0 4px;\">Pick a time to meet at the Louvre. A focused 20 minutes could be the start of something significant.</td></tr>"
        ),
        cta_label="Schedule your meeting",
        cta_url=f"{app_url}/matches",
        unsubscribe=True,
    )
    body_text = (
        f"Mutual match confirmed\n\n"
        f"Hi {first_name},\n\n"
        f"{other_name} ({other_title} at {other_company}) also accepted the connection.\n"
        f"Schedule your meeting: {app_url}/matches\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
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

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL

    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    other_first = other_name.split()[0] if other_name else other_name

    subject = f"Meeting confirmed: {first_name} and {other_first}, {meeting_time_str}"
    body_html = _render_email(
        preheader=f"Your meeting with {other_name} is booked.",
        eyebrow="Meeting booked",
        heading="Your meeting is confirmed",
        body_html=(
            f"<tr><td style=\"padding:0 0 12px;\">"
            f"  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background:#FBF8F3; border-left:3px solid #C2632A;\">"
            f"    <tr><td style=\"padding:18px 20px; font-family:-apple-system,'Poppins',Arial,sans-serif;\">"
            f"      <div style=\"font-size:12px; color:#7A7268;\">Meeting with</div>"
            f"      <div style=\"font-size:16px; font-weight:600; color:#211500; margin-bottom:12px;\">{other_name}, {other_company}</div>"
            f"      <div style=\"font-size:12px; color:#7A7268;\">When</div>"
            f"      <div style=\"font-size:15px; color:#211500; margin-bottom:12px;\">{meeting_time_str}</div>"
            f"      <div style=\"font-size:12px; color:#7A7268;\">Where</div>"
            f"      <div style=\"font-size:15px; color:#211500;\">{meeting_location}</div>"
            f"    </td></tr>"
            f"  </table>"
            f"</td></tr>"
        ),
        cta_label="View in the app",
        cta_url=f"{app_url}/matches",
        footer_note="Download the calendar invite (.ics) from your matches page to add it to your calendar.",
        unsubscribe=False,
    )
    body_text = (
        f"Meeting confirmed: {attendee_name} and {other_name}\n\n"
        f"When: {meeting_time_str}\n"
        f"Where: {meeting_location}\n\n"
        f"View and download calendar invite: {app_url}/matches\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )

    _send_email(to_email, subject, body_html, body_text)


def send_welcome_email(
    to_email: str,
    attendee_name: str,
    magic_token: str | None = None,
    app_url: str | None = None,
) -> None:
    """First-touch welcome email introducing the matchmaker, with the
    attendee's magic link. Not yet wired to a trigger."""
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    dashboard_url = f"{app_url}/m/{magic_token}" if magic_token else f"{app_url}/matches"
    subject = "Welcome to the Official Networking Tool - Proof of Talk 2026"
    body_html = _render_email(
        preheader="Your private matchmaking for Proof of Talk 2026 is ready.",
        eyebrow="Welcome",
        heading=f"Welcome, {first_name}",
        body_html=(
            "<tr><td style=\"padding:0 0 14px;\">This is the official networking tool for Proof of Talk 2026, the Louvre Palace, June 2 and 3. We use it to find the few conversations most worth your time, before you arrive.</td></tr>"
            "<tr><td style=\"padding:0 0 4px;\">Open your dashboard to see your matches, complete your profile so we can match you better, and book meetings in one tap.</td></tr>"
        ),
        cta_label="Open your matches",
        cta_url=dashboard_url,
        unsubscribe=True,
    )
    body_text = (
        f"Welcome to Proof of Talk 2026, {first_name}.\n\n"
        f"This is the official networking tool for the event at the Louvre Palace, June 2 and 3.\n"
        f"Open your matches: {dashboard_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    _send_email(to_email, subject, body_html, body_text)


# ── Post-event emails (Phase 6) ─────────────────────────────────────


def send_morning_schedule_email(
    to_email: str,
    attendee_name: str,
    meetings_today: list[dict],
    event_day: str,
    magic_token: str | None = None,
    app_url: str | None = None,
) -> None:
    """At-event morning email: "You have N meetings today" (Phase 5).

    Sent at 07:00 on each conference day (June 2 and June 3).
    meetings_today: list of dicts with keys name, company, time, location.
    event_day: "Day 1 — June 2" or "Day 2 — June 3".
    """


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
