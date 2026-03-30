"""
Weekly Master Ticket File Generator
====================================
Fetches all REAL ticket holders from Extasy API and generates an Excel file
for sharing with The Grid and internal control.

Filters out:
- Test tickets ("test ticket", "test ticket card")
- Invalid statuses (keeps only PAID, REDEEMED)

Output includes:
- Name, Email, Company, Ticket Type
- Status (PAID/REDEEMED), Order Date
- Promo Code (if used)

Usage:
    python scripts/generate_master_ticket_file.py
    python scripts/generate_master_ticket_file.py --output-dir /path/to/folder
"""

import argparse
import csv
import io
from datetime import datetime
from pathlib import Path
import httpx
import pandas as pd

# ── Extasy API ─────────────────────────────────────────────────────────────
EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_BASE     = "https://api.b2b.extasy.com/operations/reports"
ORDERS_URL      = f"{EXTASY_BASE}/orders/{EXTASY_EVENT_ID}"

# ── Filters ────────────────────────────────────────────────────────────────
TEST_TICKET_NAMES = {"test ticket", "test ticket card"}
VALID_STATUSES    = {"PAID", "REDEEMED"}

# ── Ticket-type mapping ────────────────────────────────────────────────────
TICKET_TYPE_MAP = {
    "investor pass":                    "VIP",
    "vip pass":                         "VIP",
    "vip black pass":                   "VIP",
    "general pass":                     "Delegate",
    "startup pass (application based)": "Delegate",
    "startup pass":                     "Delegate",
    "speaker pass":                     "Speaker",
    "sponsor pass":                     "Sponsor",
}

GENERIC_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}


def fetch_extasy(url: str) -> list[dict]:
    """Fetch an Extasy report endpoint. Returns list of dicts."""
    print(f"Fetching from Extasy API: {url}")
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "csv" in content_type or "text" in content_type:
            text = resp.content.decode("iso-8859-1", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]
        try:
            return resp.json()
        except Exception:
            text = resp.content.decode("iso-8859-1", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]


def map_ticket_type(ticket_name: str) -> str:
    return TICKET_TYPE_MAP.get(ticket_name.lower().strip(), "Delegate")


def is_test_ticket(ticket_name: str) -> bool:
    return ticket_name.lower().strip() in TEST_TICKET_NAMES


def extract_company(email: str) -> str:
    """Extract company name from email domain if not a generic provider."""
    if not email or "@" not in email:
        return ""
    domain = email.split("@")[1]
    if domain in GENERIC_DOMAINS:
        return ""
    return domain.replace("www.", "").split(".")[0].title()


def process_orders() -> pd.DataFrame:
    """Fetch orders from Extasy, filter, and return a DataFrame."""
    print("\n" + "="*80)
    print("FETCHING TICKET HOLDERS FROM EXTASY")
    print("="*80 + "\n")

    orders = fetch_extasy(ORDERS_URL)
    print(f"✓ Total orders fetched: {len(orders)}")

    # Filter to valid statuses
    valid = [o for o in orders if o.get("status") in VALID_STATUSES]
    print(f"✓ Valid status (PAID/REDEEMED): {len(valid)}")

    # Filter out test tickets
    real_tickets = []
    test_count = 0

    for order in valid:
        ticket_name = (order.get("ticketNames") or "").split(",")[0].strip()

        if is_test_ticket(ticket_name):
            test_count += 1
            continue

        email = (order.get("email") or "").strip().lower()
        if not email:
            continue

        first = (order.get("firstName") or "").strip()
        last = (order.get("lastName") or "").strip()
        name = f"{first} {last}".strip() or "Unknown"

        # Calculate payment info
        amount_paid = order.get("paymentsAmount", "0")
        promo_code = order.get("voucherCode", "")
        payment_method = "Full Payment" if order.get("payFullPrice", "").lower() == "true" else "Installments"

        real_tickets.append({
            "Name": name,
            "Email": email,
            "Company": extract_company(email),
            "Ticket Type": map_ticket_type(ticket_name),
            "Ticket Name": ticket_name.title(),
            "Status": order.get("status", ""),
            "Payment Method": payment_method,
            "Amount Paid (€)": amount_paid,
            "Promo Code Used": promo_code if promo_code else "None",
            "Order Date": order.get("createdAtUtc", "")[:10] if order.get("createdAtUtc") else "",  # Just date, not time
            "Order ID": order.get("id", ""),
            "Ticket Code": order.get("ticketCodes", ""),
            "Country": order.get("countryIso3Code", ""),
            "Phone": order.get("phoneNumber", ""),
        })

    print(f"✓ Test tickets filtered out: {test_count}")
    print(f"✓ Real ticket holders: {len(real_tickets)}\n")

    # Deduplicate by email, keeping highest ticket tier
    tier_order = {"Delegate": 1, "Speaker": 2, "Sponsor": 3, "VIP": 4}

    df = pd.DataFrame(real_tickets)
    df["tier_rank"] = df["Ticket Type"].map(tier_order)
    df = df.sort_values("tier_rank", ascending=False).drop_duplicates("Email", keep="first")
    df = df.drop(columns=["tier_rank"])
    df = df.sort_values(["Ticket Type", "Name"])

    print(f"✓ After deduplication: {len(df)} unique attendees\n")

    return df


def generate_summary_stats(df: pd.DataFrame) -> dict:
    """Generate summary statistics for the report."""
    promo_used = len(df[df["Promo Code Used"] != "None"])
    promo_codes = df[df["Promo Code Used"] != "None"]["Promo Code Used"].value_counts().to_dict()

    return {
        "Total Attendees": len(df),
        "By Status": df["Status"].value_counts().to_dict(),
        "By Ticket Type": df["Ticket Type"].value_counts().to_dict(),
        "By Country": df["Country"].value_counts().head(10).to_dict(),
        "By Payment Method": df["Payment Method"].value_counts().to_dict(),
        "Used Promo Code": promo_used,
        "Promo Codes Used": promo_codes,
    }


def export_to_excel(df: pd.DataFrame, output_path: Path):
    """Export DataFrame to Excel with formatting."""
    print("="*80)
    print("GENERATING EXCEL FILE")
    print("="*80 + "\n")

    stats = generate_summary_stats(df)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        # Main sheet: Ticket Holders
        df.to_excel(writer, sheet_name="Ticket Holders", index=False)

        # Summary sheet
        summary_rows = [
            ["Total Attendees", stats["Total Attendees"]],
            ["PAID", stats["By Status"].get("PAID", 0)],
            ["REDEEMED", stats["By Status"].get("REDEEMED", 0)],
            ["Used Promo Code", stats["Used Promo Code"]],
            ["", ""],
            ["VIP", stats["By Ticket Type"].get("VIP", 0)],
            ["Speaker", stats["By Ticket Type"].get("Speaker", 0)],
            ["Sponsor", stats["By Ticket Type"].get("Sponsor", 0)],
            ["Delegate", stats["By Ticket Type"].get("Delegate", 0)],
            ["", ""],
        ]

        # Add promo code breakdown
        if stats["Promo Codes Used"]:
            summary_rows.append(["Promo Codes Used:", ""])
            for code, count in stats["Promo Codes Used"].items():
                summary_rows.append([f"  {code}", count])

        summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Count"])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Format sheets
        workbook = writer.book
        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#1F4E78",
            "font_color": "white",
            "border": 1,
        })

        # Format Ticket Holders sheet
        worksheet = writer.sheets["Ticket Holders"]
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)

        # Format Summary sheet
        summary_worksheet = writer.sheets["Summary"]
        for col_num, value in enumerate(summary_df.columns.values):
            summary_worksheet.write(0, col_num, value, header_format)
            summary_worksheet.set_column(0, 0, 25)
            summary_worksheet.set_column(1, 1, 15)

    print(f"✓ Excel file created: {output_path}")
    print(f"✓ File size: {output_path.stat().st_size / 1024:.1f} KB\n")


def main():
    parser = argparse.ArgumentParser(description="Generate weekly master ticket file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "exports",
        help="Output directory for Excel file (default: backend/exports)",
    )
    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"POT2026_Master_Tickets_{timestamp}.xlsx"
    output_path = args.output_dir / filename

    print(f"\n🎫 Proof of Talk 2026 — Master Ticket File Generator")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Fetch and process
    df = process_orders()

    # Print summary
    stats = generate_summary_stats(df)
    print("="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"Total Attendees:  {stats['Total Attendees']}")
    print(f"  PAID:           {stats['By Status'].get('PAID', 0)}")
    print(f"  REDEEMED:       {stats['By Status'].get('REDEEMED', 0)}")
    print(f"  Used Promo:     {stats['Used Promo Code']}")
    print(f"\nBy Ticket Type:")
    print(f"  VIP:            {stats['By Ticket Type'].get('VIP', 0)}")
    print(f"  Speaker:        {stats['By Ticket Type'].get('Speaker', 0)}")
    print(f"  Sponsor:        {stats['By Ticket Type'].get('Sponsor', 0)}")
    print(f"  Delegate:       {stats['By Ticket Type'].get('Delegate', 0)}")

    if stats["Promo Codes Used"]:
        print(f"\nPromo Codes Used:")
        for code, count in sorted(stats["Promo Codes Used"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {code:20} {count:3} tickets")

    print("="*80 + "\n")

    # Export to Excel
    export_to_excel(df, output_path)

    print("="*80)
    print("✅ COMPLETE")
    print("="*80)
    print(f"\n📁 Master file ready for The Grid:")
    print(f"   {output_path.absolute()}\n")
    print(f"💡 Next steps:")
    print(f"   1. Review the file")
    print(f"   2. Share with The Grid team")
    print(f"   3. Archive for internal control\n")


if __name__ == "__main__":
    main()
