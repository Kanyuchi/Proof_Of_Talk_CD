"""
Rhuna/Extasy ticket audit
=========================
For every attendee that came through Rhuna, report what pass they hold
and whether it was free or paid.

Fetches live from the Extasy orders API (same source as the dashboard),
then joins to Supabase to include our mapped `ticket_type` enum.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/rhuna_ticket_audit.py

Outputs:
    backend/exports/rhuna_ticket_audit.csv
"""

import csv
import io
import os
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    sys.exit(1)

EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_ORDERS_URL = (
    f"https://api.b2b.extasy.com/operations/reports/orders/{EXTASY_EVENT_ID}"
)
TEST_TICKET_NAMES = {"test ticket", "test ticket card"}
VALID_STATUSES = {"PAID", "REDEEMED"}

EXPORT_PATH = Path(__file__).resolve().parents[1] / "exports" / "rhuna_ticket_audit.csv"


def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }


def fetch_extasy_orders() -> list[dict]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(EXTASY_ORDERS_URL)
        resp.raise_for_status()
        text = resp.content.decode("iso-8859-1", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))


def fetch_supabase_ticket_types() -> dict[str, str]:
    """email → ticket_type enum mapping from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    page_size = 1000
    offset = 0
    mapping: dict[str, str] = {}
    with httpx.Client(timeout=30) as client:
        while True:
            headers = supabase_headers() | {
                "Range-Unit": "items",
                "Range": f"{offset}-{offset + page_size - 1}",
            }
            resp = client.get(
                url,
                headers=headers,
                params={"select": "email,ticket_type", "extasy_order_id": "not.is.null"},
            )
            resp.raise_for_status()
            batch = resp.json()
            for row in batch:
                email = (row.get("email") or "").lower()
                if email:
                    mapping[email] = row.get("ticket_type") or ""
            if len(batch) < page_size:
                break
            offset += page_size
    return mapping


def parse_amount(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def classify(paid_amount: float, voucher_code: str) -> tuple[str, str]:
    if paid_amount > 0:
        return "PAID", ("voucher_discount" if voucher_code else "")
    if voucher_code:
        return "FREE", "voucher"
    return "FREE", "free_ticket"


def main() -> None:
    print("=== Rhuna/Extasy ticket audit (live) ===\n")

    print("Fetching live orders from Extasy API ...")
    orders = fetch_extasy_orders()
    print(f"  {len(orders)} total orders\n")

    print("Fetching ticket_type mapping from Supabase ...")
    supabase_tiers = fetch_supabase_ticket_types()
    print(f"  {len(supabase_tiers)} Supabase rows with extasy_order_id\n")

    output_rows: list[dict] = []
    status_counter: Counter[str] = Counter()
    ticket_counter: Counter[str] = Counter()
    tier_counter: Counter[str] = Counter()
    total_paid = 0.0
    skipped_status = 0
    skipped_test = 0

    for o in orders:
        status = o.get("status") or ""
        if status not in VALID_STATUSES:
            skipped_status += 1
            continue

        ticket_name = (o.get("ticketNames") or "").split(",")[0].strip()
        if ticket_name.lower() in TEST_TICKET_NAMES:
            skipped_test += 1
            continue

        paid_amount = parse_amount(o.get("paymentsAmount") or o.get("fullPrice"))
        voucher = (o.get("voucherCode") or "").strip()
        payment_status, comped_reason = classify(paid_amount, voucher)

        email = (o.get("email") or "").strip().lower()
        name = f"{(o.get('firstName') or '').strip()} {(o.get('lastName') or '').strip()}".strip()
        ticket_type = supabase_tiers.get(email, "(not in supabase)")

        status_counter[payment_status] += 1
        ticket_counter[ticket_name or "(unknown)"] += 1
        tier_counter[ticket_type] += 1
        total_paid += paid_amount

        output_rows.append(
            {
                "email": email,
                "name": name,
                "extasy_ticket_name": ticket_name,
                "ticket_type": ticket_type,
                "paid_amount": f"{paid_amount:.2f}",
                "voucher_code": voucher,
                "payment_status": payment_status,
                "comped_reason": comped_reason,
                "order_status": status,
                "created_at": o.get("createdAtUtc") or "",
            }
        )

    # Write CSV
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_rows.sort(key=lambda r: (r["payment_status"], r["extasy_ticket_name"], r["name"]))
    with EXPORT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"CSV written: {EXPORT_PATH}  ({len(output_rows)} valid orders)\n")

    print(f"Skipped: {skipped_status} non-PAID/REDEEMED + {skipped_test} test tickets\n")

    # Console summary
    print("── Payment status ──────────────────────────────")
    for status, count in sorted(status_counter.items(), key=lambda x: -x[1]):
        print(f"  {status:<6} {count:>4}")
    print(f"  Total revenue: €{total_paid:,.2f}\n")

    print("── Mapped tier (Supabase ticket_type) ──────────")
    for tier, count in sorted(tier_counter.items(), key=lambda x: -x[1]):
        print(f"  {tier:<20} {count:>4}")
    print()

    print("── Extasy ticket name ──────────────────────────")
    for name, count in sorted(ticket_counter.items(), key=lambda x: -x[1]):
        print(f"  {name:<45} {count:>4}")
    print()

    # FREE DELEGATE preview (the Ferd-relevant bucket)
    free_delegates = [
        r
        for r in output_rows
        if r["payment_status"] == "FREE" and r["ticket_type"] == "DELEGATE"
    ]
    print(f"── FREE DELEGATEs (n={len(free_delegates)}) — first 25 ──")
    for r in free_delegates[:25]:
        print(
            f"  {r['name']:<32} {r['extasy_ticket_name']:<38} "
            f"voucher={r['voucher_code'] or '—'}"
        )

    # PAID summary (sanity check against dashboard's €42,554)
    paid_rows = [r for r in output_rows if r["payment_status"] == "PAID"]
    print(f"\n── PAID tickets (n={len(paid_rows)}) ──")
    for r in paid_rows:
        print(
            f"  €{r['paid_amount']:>8}  {r['name']:<30} {r['extasy_ticket_name']}"
        )


if __name__ == "__main__":
    main()
