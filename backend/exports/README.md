# Master Ticket Files

This directory contains weekly master ticket files for Proof of Talk 2026.

## What's Included

Each Excel file contains:
- **Ticket Holders** sheet: Full list of real attendees with:
  - Name, Email, Company
  - Ticket Type (VIP, Speaker, Sponsor, Delegate)
  - Status (PAID/REDEEMED)
  - Order Date, Promo Code, Order ID
- **Summary** sheet: Quick statistics

## How to Generate

```bash
cd backend
source .venv/bin/activate

# Install dependencies (first time only)
pip install pandas xlsxwriter

# Generate master file for this week
python scripts/generate_master_ticket_file.py
```

Output: `POT2026_Master_Tickets_YYYY-MM-DD.xlsx`

## Weekly Workflow

1. **Monday morning**: Run the script to generate latest file
2. **Review**: Check the Summary sheet for accuracy
3. **Share**: Send to The Grid team
4. **Archive**: Keep copy for internal control

## Filters Applied

The script automatically filters out:
- ❌ Test tickets ("test ticket", "test ticket card")
- ❌ Invalid statuses (only PAID + REDEEMED)
- ❌ Duplicate emails (keeps highest ticket tier)

## File Naming

Format: `POT2026_Master_Tickets_YYYY-MM-DD.xlsx`

Example: `POT2026_Master_Tickets_2026-03-17.xlsx`
