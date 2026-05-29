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
    force: bool = False,
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

    `force=True` bypasses the EMAIL_MODE gate for a single deliberate,
    operator-initiated send (e.g. a staged welcome wave run from a script).
    It lets ops push a bounded batch to real attendees while EMAIL_MODE
    stays "allowlist" — so the *automated* triggers (match intros, mutual
    matches, password resets) remain gated until the team is ready to flip
    EMAIL_MODE=all. Never set force=True from a request-triggered path.
    """
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — email skipped")
        return False

    mode = "all" if force else (settings.EMAIL_MODE or "off").strip().lower()
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
    reply_to = (getattr(settings, "EMAIL_REPLY_TO", "") or "").strip()
    if reply_to:
        payload["reply_to"] = reply_to
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
    cta_color: str | None = None,
    footer_note: str | None = None,
    unsubscribe: bool = False,
    unsubscribe_token: str | None = None,
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
            <td align="center" bgcolor="{cta_color or accent}" style="border-radius: 4px;">
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
        if unsubscribe_token:
            unsub_url = f"{EMAIL_APP_URL}/api/v1/matches/m/{unsubscribe_token}/unsubscribe"
            prefs_url = f"{EMAIL_APP_URL}/m/{unsubscribe_token}"
        else:
            unsub_url = f"{EMAIL_APP_URL}/unsubscribe"
            prefs_url = f"{EMAIL_APP_URL}/profile"
        unsub_block = f"""
            <tr><td align="center" style="padding: 14px 0 0; font-family:{sans}; font-size:12px; color:{muted};">
              <a href="{unsub_url}" style="color:{muted}; text-decoration:underline;">Unsubscribe</a> &middot; <a href="{prefs_url}" style="color:{muted}; text-decoration:underline;">Preferences</a>
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
    force: bool = False,
) -> None:
    """Send a password reset email with a tokenized link.

    Args:
        to_email: Recipient email address.
        user_name: Full name of the user.
        reset_token: JWT reset token.
        app_url: Base URL of the app for the reset link.
        force: Bypass the EMAIL_MODE gate for this send. Password reset is
            account recovery (transactional), so it must reach real attendees
            even while EMAIL_MODE=allowlist holds back bulk engagement mail.
            Safe from the request path: rate-limited and only ever addressed to
            the email already on the User row.
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

    _send_email(to_email, subject, body_html, body_text, force=force)


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
        unsubscribe_token=magic_token,
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


def send_match_digest_email(
    to_email: str,
    attendee_name: str,
    new_count: int,
    top_match_name: str,
    top_match_title: str,
    top_match_company: str,
    top_explanation: str,
    magic_token: str | None = None,
    app_url: str | None = None,
    force: bool = False,
) -> bool:
    """"N new top matches" digest. Fires from a daily cron for existing
    attendees whose curated pool gained >=3 new matches since the last digest.

    `force=True` is for the cron path (off the request path); never call with
    force=True from a request handler.
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    dashboard_url = f"{app_url}/m/{magic_token}" if magic_token else f"{app_url}/matches"
    noun = "match" if new_count == 1 else "matches"
    short_explanation = (
        top_explanation[:220] + "…" if len(top_explanation) > 220 else top_explanation
    )

    subject = f"{first_name}, {new_count} new top {noun} for Proof of Talk 2026"
    body_html = _render_email(
        preheader=f"{new_count} new high-quality {noun} since your last visit.",
        eyebrow="New introductions",
        heading=f"{new_count} new top {noun} for you",
        body_html=(
            f"<tr><td style=\"padding:0 0 16px;\">Hi {first_name}, since you last checked in, "
            f"the Matchmaker added {new_count} new top-tier {noun} to your pool — ranked by who is "
            f"most worth your time at the Louvre.</td></tr>"
            f"<tr><td style=\"padding:0 0 8px;\">"
            f"  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background:#FBF8F3; border-left:3px solid #C2632A;\">"
            f"    <tr><td style=\"padding:18px 20px;\">"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#C2632A; margin-bottom:8px;\">Featured new introduction</div>"
            f"      <div style=\"font-family:Georgia,'Playfair Display',serif; font-size:18px; color:#211500; font-weight:600;\">{top_match_name}</div>"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:13px; color:#7A7268; margin-bottom:10px;\">{top_match_title}, {top_match_company}</div>"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:14px; line-height:1.6; color:#3A3A3A;\">{short_explanation}</div>"
            f"    </td></tr>"
            f"  </table>"
            f"</td></tr>"
        ),
        cta_label=f"See all {new_count} new {noun}",
        cta_url=dashboard_url,
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )
    body_text = (
        f"{new_count} new top {noun} for Proof of Talk 2026, {first_name}.\n\n"
        f"Since your last visit, the Matchmaker added {new_count} new top-tier {noun} to your pool.\n\n"
        f"Featured: {top_match_name}, {top_match_title} at {top_match_company}\n\n"
        f"{short_explanation}\n\n"
        f"View all: {dashboard_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    return _send_email(to_email, subject, body_html, body_text, force=force)


def send_mutual_match_email(
    to_email: str,
    attendee_name: str,
    other_name: str,
    other_title: str,
    other_company: str,
    app_url: str | None = None,
    magic_token: str | None = None,
    force: bool = False,
) -> bool:
    """Send a 'mutual match confirmed' notification email.

    Args:
        to_email: Recipient email.
        attendee_name: Name of the recipient.
        other_name: Name of the other party who accepted.
        other_title: Title of the other party.
        other_company: Company of the other party.
        app_url: Base URL of the app for the CTA link.
        magic_token: Recipient's magic_access_token for personalised unsubscribe link.
        force: Bypass EMAIL_MODE gate (for the reciprocity_notify cron). Never
            set from a request path — see _send_email docstring.
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
        unsubscribe_token=magic_token,
    )
    body_text = (
        f"Mutual match confirmed\n\n"
        f"Hi {first_name},\n\n"
        f"{other_name} ({other_title} at {other_company}) also accepted the connection.\n"
        f"Schedule your meeting: {app_url}/matches\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )

    return _send_email(to_email, subject, body_html, body_text, force=force)


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
    force: bool = False,
) -> bool:
    """First-touch welcome email introducing the matchmaker, with the
    attendee's magic link.

    `force=True` is for the operator-run staged batch (send_welcome_batch.py)
    and bypasses the EMAIL_MODE gate for this one send. Returns the send
    result so the batch script can tally successes/failures.
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    # CTA lands on the magic-link page with the "Unlock full access" panel
    # pre-opened (?unlock=1) so they go straight to setting a password.
    unlock_url = f"{app_url}/m/{magic_token}?unlock=1" if magic_token else f"{app_url}/register"
    subject = "Welcome to the Official Networking Tool - Proof of Talk 2026"
    body_html = _render_email(
        preheader="Your private matchmaking for Proof of Talk 2026 is ready.",
        eyebrow="Welcome",
        heading=f"Welcome, {first_name}",
        body_html=(
            "<tr><td style=\"padding:0 0 14px;\">This is the official networking tool for Proof of Talk 2026, the Louvre Palace, June 2 and 3. We use it to find the few conversations most worth your time, before you arrive.</td></tr>"
            "<tr><td style=\"padding:0 0 14px;\">You are already pre-logged in with the <strong>same email you used to buy your ticket</strong>. It is the same address you are reading this email from. Click below to set your password and unlock full access: see your matches, message them, and book meetings in one tap.</td></tr>"
        ),
        cta_label="Unlock Full Access",
        cta_url=unlock_url,
        cta_color="#E76315",
        footer_note="On your phone? Add it to your home screen for one-tap access all event. It runs full-screen like a real app, no App Store needed.",
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )
    body_text = (
        f"Welcome to Proof of Talk 2026, {first_name}.\n\n"
        f"This is the official networking tool for the event at the Louvre Palace, June 2 and 3.\n\n"
        f"You are already pre-logged in with the same email you used to buy your ticket. "
        f"It is the same address you are reading this email from.\n"
        f"Click to set your password and unlock full access: {unlock_url}\n\n"
        f"On your phone? Add it to your home screen for one-tap access all event. "
        f"It runs full-screen like a real app, no App Store needed.\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    return _send_email(to_email, subject, body_html, body_text, force=force)


def send_interest_notification(
    to_email: str,
    attendee_name: str,
    count: int,
    magic_token: str | None = None,
    app_url: str | None = None,
    force: bool = False,
) -> bool:
    """"N people want to meet you" pull-back email. The CTA lands on the
    magic-link Requests tab so a no-login attendee can accept back in one tap.

    `force=True` is for the operator backlog batch (notify_pending_interest.py)
    and the future recurring cron — both off the request path. Never call with
    force=True from a request handler (see _send_email docstring).
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    requests_url = (
        f"{app_url}/m/{magic_token}?tab=requests" if magic_token else f"{app_url}/matches"
    )
    noun = "person wants" if count == 1 else "people want"
    subject = f"{count} {noun} to meet you at Proof of Talk"
    body_html = _render_email(
        preheader=f"{count} {noun} to meet you. Accept to lock in the meeting.",
        eyebrow="Mutual interest",
        heading=f"{count} {noun} to meet you",
        body_html=(
            f"<tr><td style=\"padding:0 0 14px;\">Hi {first_name}, {count} {noun} to meet you at "
            f"Proof of Talk 2026. They have already said yes. Accept them back and you can book a "
            f"meeting in one tap, no login needed.</td></tr>"
        ),
        cta_label="See who wants to meet you",
        cta_url=requests_url,
        cta_color="#E76315",
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )
    body_text = (
        f"{count} {noun} to meet you at Proof of Talk 2026, {first_name}.\n\n"
        f"They have already said yes. Accept them back and book a meeting in one tap:\n"
        f"{requests_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    return _send_email(to_email, subject, body_html, body_text, force=force)


# ── Pre-event emails ─────────────────────────────────────────────────


def send_t_minus_one_reminder_email(
    to_email: str,
    attendee_name: str,
    top_matches: list,
    scheduled_count: int,
    total_matches: int,
    magic_token: str | None = None,
    app_url: str | None = None,
    force: bool = False,
) -> bool:
    """T-1 reminder ("Tomorrow at the Louvre"), fired once at 17:00 Paris on
    2026-06-01 from a date-bound CronTrigger. Force-sends off the request path.

    top_matches: list of {name, title, company} dicts, max 3.
    scheduled_count: how many meetings the attendee already has booked.
    total_matches: total curated+priority_intro pool size.
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    if not top_matches:
        return False
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    dashboard_url = f"{app_url}/m/{magic_token}" if magic_token else f"{app_url}/matches"
    unbooked = max(0, total_matches - scheduled_count)

    if scheduled_count == 0:
        scheduled_line = "You have no meetings booked yet."
    elif scheduled_count == 1:
        scheduled_line = "You have 1 meeting booked."
    else:
        scheduled_line = f"You have {scheduled_count} meetings booked."

    if unbooked > 0:
        book_line = f"Book {min(unbooked, 5)} more before tomorrow morning."
    else:
        book_line = ""

    subject = f"Tomorrow at the Louvre, {first_name}"

    # Render the top-3 as a vertical list of small cream cards.
    cards = ""
    for i, m in enumerate(top_matches[:3], 1):
        name = (m.get("name") or "").strip() or "Top match"
        title = (m.get("title") or "").strip()
        company = (m.get("company") or "").strip()
        meta = ", ".join(x for x in (title, company) if x) or ""
        cards += (
            f"<tr><td style=\"padding:0 0 10px;\">"
            f"  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background:#FBF8F3; border-left:3px solid #C2632A;\">"
            f"    <tr><td style=\"padding:14px 18px;\">"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:10px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#C2632A; margin-bottom:6px;\">#{i}</div>"
            f"      <div style=\"font-family:Georgia,'Playfair Display',serif; font-size:17px; color:#211500; font-weight:600;\">{name}</div>"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:13px; color:#7A7268;\">{meta}</div>"
            f"    </td></tr>"
            f"  </table>"
            f"</td></tr>"
        )

    body_html = _render_email(
        preheader=f"The Louvre is tomorrow. {scheduled_line}",
        eyebrow="Tomorrow at the Louvre",
        heading=f"{first_name}, the Louvre is tomorrow",
        body_html=(
            f"<tr><td style=\"padding:0 0 14px;\">Proof of Talk opens at the Louvre Palace at 9:00 Paris time tomorrow. Here are your top 3 introductions for the two days:</td></tr>"
            f"{cards}"
            f"<tr><td style=\"padding:8px 0 4px; font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:14px; color:#3A3A3A;\">{scheduled_line} {book_line}</td></tr>"
        ),
        cta_label="Review your matches",
        cta_url=dashboard_url,
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )
    body_text_matches = "\n".join(
        f"  #{i}. {m.get('name','')} - {m.get('title','')}, {m.get('company','')}"
        for i, m in enumerate(top_matches[:3], 1)
    )
    body_text = (
        f"Tomorrow at the Louvre, {first_name}.\n\n"
        f"Proof of Talk opens at 9:00 Paris time tomorrow.\n\n"
        f"Your top 3 introductions:\n"
        f"{body_text_matches}\n\n"
        f"{scheduled_line} {book_line}\n\n"
        f"Review your matches: {dashboard_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    return _send_email(to_email, subject, body_html, body_text, force=force)


# ── Post-event emails (Phase 6) ─────────────────────────────────────


def send_morning_schedule_email(
    to_email: str,
    attendee_name: str,
    meetings_today: list[dict],
    event_day: str,
    magic_token: str | None = None,
    app_url: str | None = None,
    force: bool = False,
) -> bool:
    """At-event morning email: "You have N meetings today" (Phase 5).

    Sent at 07:00 Europe/Paris on each conference day (June 2 and June 3).
    meetings_today: list of dicts with keys name, company, time, location.
    event_day: "Day 1 - June 2" or "Day 2 - June 3".

    `force=True` is for the morning-schedule cron (off the request path).
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    if not meetings_today:
        return False
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    matches_url = f"{app_url}/m/{magic_token}" if magic_token else f"{app_url}/matches"
    n = len(meetings_today)
    noun = "meeting" if n == 1 else "meetings"

    rows = []
    for m in meetings_today:
        rows.append(
            f"<tr><td style=\"padding:14px 20px; background:#FBF8F3; border-left:3px solid #C2632A;\">"
            f"  <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:12px; font-weight:700; letter-spacing:0.08em; color:#C2632A;\">{m['time']}</div>"
            f"  <div style=\"font-family:Georgia,'Playfair Display',serif; font-size:17px; color:#211500; font-weight:600; margin-top:4px;\">{m['name']}</div>"
            f"  <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:13px; color:#7A7268;\">{m['company']}</div>"
            f"  <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:12px; color:#7A7268; margin-top:6px;\">{m['location']}</div>"
            f"</td></tr>"
            f"<tr><td style=\"height:10px; line-height:10px;\">&nbsp;</td></tr>"
        )
    meetings_block = (
        f"<tr><td style=\"padding:0 0 12px;\">"
        f"  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\">{''.join(rows)}</table>"
        f"</td></tr>"
    )

    subject = f"{first_name}, you have {n} {noun} at the Louvre today"
    body_html = _render_email(
        preheader=f"{n} {noun} scheduled for {event_day}. Tap to open your schedule.",
        eyebrow=event_day,
        heading=f"Today at the Louvre, {first_name}",
        body_html=(
            f"<tr><td style=\"padding:0 0 14px;\">You have <strong>{n} {noun}</strong> booked today. The day moves fast - here is your schedule.</td></tr>"
            + meetings_block
        ),
        cta_label="Open your schedule",
        cta_url=matches_url,
        cta_color="#E76315",
        footer_note="Times are local (Paris). Plus-or-minus 5 minutes is normal - the room number is the source of truth.",
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )

    lines = [f"Today at the Louvre, {first_name}", "", f"You have {n} {noun} booked today.", ""]
    for m in meetings_today:
        lines.append(f"{m['time']} - {m['name']} ({m['company']}) - {m['location']}")
    lines.extend(["", f"Open your schedule: {matches_url}", "", "Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"])
    body_text = "\n".join(lines)

    return _send_email(to_email, subject, body_html, body_text, force=force)


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
