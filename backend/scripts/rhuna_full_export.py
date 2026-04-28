"""
Rhuna full export — Orders + Tickets joined
============================================
Snapshot every Rhuna attendee (paid, comped, failed, refunded, pending)
with every field both endpoints expose.

Grain: one row per ticket holder.
- Orders that have tickets  → one row per ticket (join on orderId)
- Orders with no tickets yet → one row with empty ticket fields
  (status = FAILED / REFUNDED / PAYMENT_PENDING)

The CSV is self-contained — paste into a fresh Google Sheet, freeze row 1,
done. No Supabase dependency, no auth.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/rhuna_full_export.py

Output:
    backend/exports/rhuna_full_export.csv
"""

import csv
import io
from collections import defaultdict
from pathlib import Path

import httpx

EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_BASE = "https://api.b2b.extasy.com/operations/reports"
ORDERS_URL = f"{EXTASY_BASE}/orders/{EXTASY_EVENT_ID}"
TICKETS_URL = f"{EXTASY_BASE}/tickets/{EXTASY_EVENT_ID}"

EXPORT_PATH = Path("/Users/kanyuchi/Desktop/Master_File/rhuna_full_export.csv")

# ── Column layout ─────────────────────────────────────────────────────────────
# Prefixed so it's obvious which endpoint each field comes from when Ferd
# (or anyone else) is reading the sheet.
ORDER_FIELDS = [
    "id", "displayOn", "firstName", "lastName", "phoneNumber", "email",
    "city", "county", "countryIso3Code", "nationalityIso3Code",
    "createdAtUtc", "fullPrice", "payFullPrice", "payInstallments", "status",
    "voucherCode", "voucherAmount", "voucherType",
    "numberOfTickets", "ticketCodes", "ticketNames",
    "paymentsStatus", "paymentsAmount", "ticketsId",
]

TICKET_FIELDS = [
    "id", "orderId", "displayOn", "name", "editionName",
    "priceWithVoucherIfApplied", "discountPriceWithVoucherIfApplied",
    "discountEndDate", "boughtDate",
    "hasVoucher", "voucherValue", "voucherName", "voucherCode",
    "ticketCodes", "ticketOwners",
]


def fetch_csv(url: str) -> list[dict]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        text = resp.content.decode("iso-8859-1", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))


def to_float(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_ticket_owner(ticket_owners: str) -> str:
    """ticketOwners is formatted 'Full Name - +phonenumber'. Strip the phone."""
    if not ticket_owners:
        return ""
    return ticket_owners.split(" - ")[0].strip()


def classify_payment(order: dict) -> str:
    """Derive payment_status: PAID / FREE / FAILED / REFUNDED / PAYMENT_PENDING."""
    paid = to_float(order.get("paymentsAmount"))
    raw_status = order.get("status") or "UNKNOWN"
    if raw_status in {"PAID", "REDEEMED"}:
        return "PAID" if paid > 0 else "FREE"
    return raw_status


def main() -> None:
    print("=== Rhuna full export (Orders + Tickets joined) ===\n")

    print(f"Fetching orders  ... {ORDERS_URL}")
    orders = fetch_csv(ORDERS_URL)
    print(f"  {len(orders)} orders\n")

    print(f"Fetching tickets ... {TICKETS_URL}")
    tickets = fetch_csv(TICKETS_URL)
    print(f"  {len(tickets)} tickets\n")

    # Index tickets by orderId for O(1) join
    tickets_by_order: dict[str, list[dict]] = defaultdict(list)
    for t in tickets:
        tickets_by_order[t.get("orderId") or ""].append(t)

    # ── Column schema ─────────────────────────────────────────────────────
    # 1. derived "summary" columns first (what Ferd actually reads)
    # 2. all raw Order fields, order_ prefixed
    # 3. all raw Ticket fields, ticket_ prefixed
    summary_fields = [
        "attendee_name",          # ticket_owner if present, else order buyer
        "buyer_name",             # always the order buyer
        "email",
        "country_iso3",
        "ticket_name",
        "order_status",           # raw Rhuna status
        "payment_status",         # derived: PAID / FREE / FAILED / REFUNDED / PAYMENT_PENDING
        "list_price_eur",
        "paid_amount_eur",
        "discount_eur",
        "voucher_code",
        "voucher_type",
        "is_reassigned_ticket",   # TRUE when ticketOwners differs from buyer
    ]
    order_cols = [f"order_{f}" for f in ORDER_FIELDS]
    ticket_cols = [f"ticket_{f}" for f in TICKET_FIELDS]
    header = summary_fields + order_cols + ticket_cols

    rows: list[dict] = []
    orders_with_tickets = orders_without_tickets = extra_ticket_rows = 0

    for order in orders:
        payment_status = classify_payment(order)
        order_list_price = to_float(order.get("fullPrice"))
        order_paid_amount = to_float(order.get("paymentsAmount"))
        buyer_name = f"{(order.get('firstName') or '').strip()} {(order.get('lastName') or '').strip()}".strip()
        order_id = order.get("id") or ""
        order_tickets = tickets_by_order.get(order_id, [])

        order_prefixed = {f"order_{k}": (order.get(k) or "") for k in ORDER_FIELDS}
        blank_ticket = {f"ticket_{k}": "" for k in TICKET_FIELDS}

        base_common = {
            "buyer_name": buyer_name,
            "email": (order.get("email") or "").strip().lower(),
            "country_iso3": order.get("countryIso3Code") or "",
            "ticket_name": (order.get("ticketNames") or "").split(",")[0].strip(),
            "order_status": order.get("status") or "",
            "payment_status": payment_status,
            "voucher_code": order.get("voucherCode") or "",
            "voucher_type": order.get("voucherType") or "",
        }

        if not order_tickets:
            # Order has no ticket row (failed, refunded, pending, or not yet issued).
            # Use order-level price/paid so this row still shows funnel value.
            orders_without_tickets += 1
            discount = max(order_list_price - order_paid_amount, 0.0)
            row = {
                **base_common,
                "attendee_name": buyer_name,
                "list_price_eur": f"{order_list_price:.2f}",
                "paid_amount_eur": f"{order_paid_amount:.2f}",
                "discount_eur": f"{discount:.2f}",
                "is_reassigned_ticket": "FALSE",
                **order_prefixed,
                **blank_ticket,
            }
            rows.append(row)
            continue

        orders_with_tickets += 1
        if len(order_tickets) > 1:
            extra_ticket_rows += len(order_tickets) - 1

        # Per-ticket prices come from Tickets endpoint (priceWithVoucherIfApplied
        # is the actual amount for that ticket). Prevents double-counting when
        # one order contains multiple tickets.
        for t in order_tickets:
            ticket_owner_clean = clean_ticket_owner(t.get("ticketOwners") or "")
            attendee_name = ticket_owner_clean or buyer_name
            owner_norm = " ".join(ticket_owner_clean.lower().split())
            buyer_norm = " ".join(buyer_name.lower().split())
            is_reassigned = (
                "TRUE" if ticket_owner_clean and owner_norm != buyer_norm else "FALSE"
            )

            ticket_paid = to_float(t.get("priceWithVoucherIfApplied"))
            ticket_list = ticket_paid + to_float(t.get("discountPriceWithVoucherIfApplied"))
            ticket_discount = max(ticket_list - ticket_paid, 0.0)

            ticket_prefixed = {f"ticket_{k}": (t.get(k) or "") for k in TICKET_FIELDS}
            row = {
                **base_common,
                "attendee_name": attendee_name,
                "list_price_eur": f"{ticket_list:.2f}",
                "paid_amount_eur": f"{ticket_paid:.2f}",
                "discount_eur": f"{ticket_discount:.2f}",
                "is_reassigned_ticket": is_reassigned,
                **order_prefixed,
                **ticket_prefixed,
            }
            rows.append(row)

    # ── Write CSV ─────────────────────────────────────────────────────────
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EXPORT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV written: {EXPORT_PATH}\n")

    # ── Summary stats ─────────────────────────────────────────────────────
    from collections import Counter
    status_counter: Counter[str] = Counter(r["payment_status"] for r in rows)
    order_status_counter: Counter[str] = Counter(r["order_status"] for r in rows)
    pass_counter: Counter[str] = Counter(r["ticket_name"] for r in rows)
    reassigned = sum(1 for r in rows if r["is_reassigned_ticket"] == "TRUE")
    total_paid = sum(float(r["paid_amount_eur"]) for r in rows if r["payment_status"] == "PAID")
    total_discount = sum(float(r["discount_eur"]) for r in rows)

    print(f"Total rows written:        {len(rows)}")
    print(f"  Orders with tickets:     {orders_with_tickets}")
    print(f"  Orders without tickets:  {orders_without_tickets} (failed / pending / not issued)")
    print(f"  Extra rows from multi-ticket orders: +{extra_ticket_rows}")
    print(f"  Reassigned tickets:      {reassigned} (ticketOwners ≠ buyer)\n")

    print("── Payment status (derived) ─────────────────")
    for s, c in sorted(status_counter.items(), key=lambda x: -x[1]):
        print(f"  {s:<20} {c:>4}")
    print()

    print("── Order status (raw Rhuna) ─────────────────")
    for s, c in sorted(order_status_counter.items(), key=lambda x: -x[1]):
        print(f"  {s:<20} {c:>4}")
    print()

    print("── Ticket name ──────────────────────────────")
    for n, c in sorted(pass_counter.items(), key=lambda x: -x[1]):
        print(f"  {n:<45} {c:>4}")
    print()

    print(f"Total revenue (PAID only):  €{total_paid:,.2f}")
    print(f"Total discount given:       €{total_discount:,.2f}")


if __name__ == "__main__":
    main()
