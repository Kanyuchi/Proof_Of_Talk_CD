"""
Quick audit: fetch ALL orders from Extasy and show distinct statuses + counts.
No writes — read-only.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/extasy_status_audit.py
"""

import csv
import io
from collections import Counter

import httpx

EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
ORDERS_URL = f"https://api.b2b.extasy.com/operations/reports/orders/{EXTASY_EVENT_ID}"

TEST_TICKET_NAMES = {"test ticket", "test ticket card"}


def fetch_orders() -> list[dict]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(ORDERS_URL)
        resp.raise_for_status()
        text = resp.content.decode("iso-8859-1", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)


def main():
    print("Fetching ALL orders from Extasy...\n")
    orders = fetch_orders()
    print(f"Total orders: {len(orders)}\n")

    # Show all CSV column names
    if orders:
        print(f"CSV columns: {list(orders[0].keys())}\n")

    # 1. Status breakdown
    status_counts = Counter(o.get("status", "???") for o in orders)
    print("── Status breakdown ──")
    for status, count in status_counts.most_common():
        print(f"  {count:>4}x  {status}")

    # 2. For each status, show payment amount range
    print("\n── Payment amounts by status ──")
    for status in sorted(status_counts.keys()):
        amounts = []
        for o in orders:
            if o.get("status") == status:
                try:
                    amounts.append(float(o.get("paymentsAmount") or 0))
                except ValueError:
                    amounts.append(0)
        if amounts:
            print(f"  {status}: min={min(amounts):.2f}, max={max(amounts):.2f}, avg={sum(amounts)/len(amounts):.2f}")

    # 3. Non-PAID orders detail (the ones we're currently missing)
    non_paid = [o for o in orders if o.get("status") != "PAID"]
    if non_paid:
        print(f"\n── Non-PAID orders ({len(non_paid)} total) ──")
        for o in non_paid:
            ticket = (o.get("ticketNames") or "").split(",")[0].strip()
            is_test = ticket.lower().strip() in TEST_TICKET_NAMES
            first = (o.get("firstName") or "").strip()
            last = (o.get("lastName") or "").strip()
            email = (o.get("email") or "").strip().lower()
            amount = o.get("paymentsAmount", "?")
            status = o.get("status", "?")
            test_flag = " [TEST]" if is_test else ""
            print(f"  {status:<12} ${amount:<10} {first} {last:<20} <{email}>  [{ticket}]{test_flag}")
    else:
        print("\n  No non-PAID orders found.")

    # 4. Summary of what we'd gain
    non_paid_real = [
        o for o in non_paid
        if (o.get("ticketNames") or "").split(",")[0].strip().lower() not in TEST_TICKET_NAMES
        and (o.get("email") or "").strip()
    ]
    print(f"\n── Summary ──")
    print(f"  Currently ingesting (PAID only):     {status_counts.get('PAID', 0)}")
    print(f"  Non-PAID, non-test, with email:      {len(non_paid_real)}")
    print(f"  Would bring total to:                {status_counts.get('PAID', 0) + len(non_paid_real)}")


if __name__ == "__main__":
    main()
