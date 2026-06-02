"""One-off: send corrected meeting confirmation to Olga Shpunyakova.

Glen Cameron <-> Olga Shpunyakova match was stored as 11:00 UTC (= 13:00 Paris).
The original auto-email mislabeled it "11:00 (Louvre time)". This resends the
correct time (13:00 Tue Jun 2, Louvre time) and the B2B Lounge location.

Forced send: EMAIL_MODE is "off"/"allowlist", so this bypasses the gate for a
single deliberate operator send (not on any request path).

Run: python scripts/send_olga_glen_confirmation.py
"""
from app.services.email import send_meeting_confirmation_email

OLGA_EMAIL = "olgabonney@gmail.com"

if __name__ == "__main__":
    send_meeting_confirmation_email(
        to_email=OLGA_EMAIL,
        attendee_name="Olga Shpunyakova",
        other_name="Glen Cameron",
        other_company="Zombie Delete (TAV)",
        meeting_time_str="Tue Jun 2 · 13:00 (Louvre time)",
        meeting_location="B2B Lounge, Louvre Palace",
        force=True,
    )
    print(f"Sent corrected confirmation to {OLGA_EMAIL}")
