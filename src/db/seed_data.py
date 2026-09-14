import json
import sqlite3
from datetime import datetime, timezone
from src.db.client import db

def seed_database():
    """Seed synthetic loan files into the active database (Supabase or SQLite)."""
    now = datetime.now(timezone.utc).isoformat()

    # 1. Loan L-20417
    loan = {
        "id": "L-20417",
        "borrower_name": "John Doe",
        "property_address": "123 Elm St, Austin, TX 78701",
        "program": "conv_30_fixed",
        "purpose": "purchase",
        "occupancy": "primary",
        "loan_amount": 450000.00,
        "interest_rate": 6.875,
        "milestone": "conditional_approval",
        "lock_status": "locked",
        "locked_at": "2026-02-18T10:00:00Z",
        "version": 1,
        "created_at": now
    }

    if db.use_supabase:
        db.supabase.table("loans").upsert(loan).execute()
    else:
        conn = db._get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO loans (id, borrower_name, property_address, program, purpose, occupancy, loan_amount, interest_rate, milestone, lock_status, locked_at, version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (loan["id"], loan["borrower_name"], loan["property_address"], loan["program"], loan["purpose"], loan["occupancy"], loan["loan_amount"], loan["interest_rate"], loan["milestone"], loan["lock_status"], loan["locked_at"], loan["version"], loan["created_at"])
        )
        conn.commit()
        conn.close()

    # 2. Documents
    docs = [
        {
            "id": "DOC-BANK-01",
            "loan_id": "L-20417",
            "type": "bank_statement",
            "borrower_name": "John Doe",
            "page_count": 2,
            "status": "indexed",
            "metadata": {
                "institution": "First National Bank",
                "account_number": "XXXX-4412",
                "ending_balance": 24500.00,
                "statement_period": "2026-02-01 to 2026-02-28",
                "large_deposits": [
                    {"date": "2026-02-24", "amount": 8500.00, "description": "WIRE TRANSFER ELEANOR VANCE", "type": "wire"}
                ]
            },
            "created_at": now
        },
        {
            "id": "DOC-GIFT-01",
            "loan_id": "L-20417",
            "type": "gift_letter",
            "borrower_name": "John Doe",
            "page_count": 1,
            "status": "indexed",
            "metadata": {
                "donor_name": "Eleanor Vance",
                "relationship": "Mother",
                "gift_amount": 8500.00,
                "subject_property": "123 Elm St, Austin, TX 78701",
                "no_repayment": True
            },
            "created_at": now
        },
        {
            "id": "DOC-WIRE-01",
            "loan_id": "L-20417",
            "type": "transfer_receipt",
            "borrower_name": "John Doe",
            "page_count": 1,
            "status": "indexed",
            "metadata": {
                "wire_confirmation": "FED-WIRE-8891024",
                "sender": "Eleanor Vance",
                "recipient": "John Doe",
                "amount": 8500.00,
                "date": "2026-02-24"
            },
            "created_at": now
        },
        {
            "id": "DOC-PAYSTUB-01",
            "loan_id": "L-20417",
            "type": "paystub",
            "borrower_name": "John Doe",
            "page_count": 1,
            "status": "indexed",
            "metadata": {
                "employer": "Acme Corp",
                "pay_period_end": "2026-01-31",
                "monthly_base_salary": 6000.00,
                "ytd_earnings": 6000.00
            },
            "created_at": now
        },
        {
            "id": "DOC-FEESHEET-01",
            "loan_id": "L-20417",
            "type": "title_fee_sheet",
            "borrower_name": "John Doe",
            "page_count": 1,
            "status": "indexed",
            "metadata": {
                "title_company": "Lone Star Title Co",
                "title_lenders_policy": 1020.00,
                "settlement_fee": 640.00
            },
            "created_at": now
        }
    ]

    for d in docs:
        meta_json = json.dumps(d["metadata"])
        if db.use_supabase:
            db.supabase.table("documents").upsert({
                "id": d["id"],
                "loan_id": d["loan_id"],
                "type": d["type"],
                "borrower_name": d["borrower_name"],
                "page_count": d["page_count"],
                "status": d["status"],
                "metadata": d["metadata"],
                "created_at": d["created_at"]
            }).execute()
        else:
            conn = db._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO documents (id, loan_id, type, borrower_name, page_count, status, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (d["id"], d["loan_id"], d["type"], d["borrower_name"], d["page_count"], d["status"], meta_json, d["created_at"])
            )
            conn.commit()
            conn.close()

    # 3. Disclosures & Fees (Deck Worked Example T-1)
    disclosures = [
        {
            "id": "LE-2",
            "loan_id": "L-20417",
            "type": "LE",
            "version": 2,
            "issued_date": "2026-02-20",
            "received_date": "2026-02-20",
            "receipt_method": "e_ack",
            "apr": 6.912,
            "loan_product": "conv_30_fixed",
            "prepay_penalty": False,
            "lender_credits": 0.00,
            "baseline_ref": None,
            "created_at": now,
            "fees": [
                {"code": "origination", "label": "Origination Charge", "section": "A", "amount": 1200.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 1200.00},
                {"code": "appraisal", "label": "Appraisal Fee", "section": "B", "amount": 550.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 550.00},
                {"code": "transfer_taxes", "label": "Transfer Taxes", "section": "E", "amount": 2100.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 2100.00},
                {"code": "title_lenders_policy", "label": "Title - Lender's Policy", "section": "C", "amount": 900.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": True, "baseline_amount": 900.00},
                {"code": "settlement_fee", "label": "Settlement Fee", "section": "C", "amount": 600.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": True, "baseline_amount": 600.00},
                {"code": "recording", "label": "Recording Fees", "section": "E", "amount": 180.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 180.00},
                {"code": "pest_inspection", "label": "Pest Inspection", "section": "C", "amount": 150.00, "payee_affiliated": False, "borrower_shopped": True, "on_spl": False, "baseline_amount": 150.00}
            ]
        },
        {
            "id": "CD-1",
            "loan_id": "L-20417",
            "type": "CD",
            "version": 1,
            "issued_date": "2026-03-18",
            "received_date": "2026-03-19",
            "receipt_method": "e_ack",
            "apr": 6.948,
            "loan_product": "conv_30_fixed",
            "prepay_penalty": False,
            "lender_credits": 0.00,
            "baseline_ref": "LE-2",
            "created_at": now,
            "fees": [
                {"code": "origination", "label": "Origination Charge", "section": "A", "amount": 1200.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 1200.00},
                {"code": "appraisal", "label": "Appraisal Fee", "section": "B", "amount": 650.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 550.00},
                {"code": "transfer_taxes", "label": "Transfer Taxes", "section": "E", "amount": 2100.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 2100.00},
                {"code": "title_lenders_policy", "label": "Title - Lender's Policy", "section": "C", "amount": 1020.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": True, "baseline_amount": 900.00},
                {"code": "settlement_fee", "label": "Settlement Fee", "section": "C", "amount": 640.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": True, "baseline_amount": 600.00},
                {"code": "recording", "label": "Recording Fees", "section": "E", "amount": 200.00, "payee_affiliated": False, "borrower_shopped": False, "on_spl": False, "baseline_amount": 180.00},
                {"code": "pest_inspection", "label": "Pest Inspection", "section": "C", "amount": 175.00, "payee_affiliated": False, "borrower_shopped": True, "on_spl": False, "baseline_amount": 150.00}
            ]
        }
    ]

    for disc in disclosures:
        fees = disc.pop("fees")
        if db.use_supabase:
            db.supabase.table("disclosures").upsert(disc).execute()
            for f in fees:
                f_record = dict(f)
                f_record["id"] = f"{disc['id']}-{f['code']}"
                f_record["disclosure_id"] = disc["id"]
                f_record["created_at"] = now
                db.supabase.table("fees").upsert(f_record).execute()
        else:
            conn = db._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO disclosures (id, loan_id, type, version, issued_date, received_date, receipt_method, apr, loan_product, prepay_penalty, lender_credits, baseline_ref, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (disc["id"], disc["loan_id"], disc["type"], disc["version"], disc["issued_date"], disc["received_date"], disc["receipt_method"], disc["apr"], disc["loan_product"], 1 if disc["prepay_penalty"] else 0, disc["lender_credits"], disc["baseline_ref"], disc["created_at"])
            )
            for f in fees:
                f_id = f"{disc['id']}-{f['code']}"
                conn.execute(
                    "INSERT OR REPLACE INTO fees (id, disclosure_id, code, label, section, amount, payee, payee_affiliated, borrower_shopped, on_spl, baseline_amount, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f_id, disc["id"], f["code"], f["label"], f["section"], f["amount"], f.get("payee"), 1 if f["payee_affiliated"] else 0, 1 if f["borrower_shopped"] else 0, 1 if f["on_spl"] else 0, f["baseline_amount"], now)
                )
            conn.commit()
            conn.close()

    # 4. Underwriting Conditions for L-20417
    conditions = [
        {
            "id": "COND-PTD-07",
            "loan_id": "L-20417",
            "category": "PTD",
            "code": "PTD-07",
            "title": "Large Deposit Verification",
            "description": "Source $8,500 deposit on checking account ending 4412 dated 02/24/2026 per Fannie Mae large deposit guidelines.",
            "cited_rule": "Fannie Mae Selling Guide B3-4.2-02",
            "status": "open",
            "owner": "borrower",
            "evidence": [
                {"doc_id": "DOC-BANK-01", "page_number": 2, "description": "Bank statement showing $8,500 wire transfer deposit", "verified": True},
                {"doc_id": "DOC-GIFT-01", "page_number": 1, "description": "Signed gift letter from Mother Eleanor Vance for $8,500", "verified": True},
                {"doc_id": "DOC-WIRE-01", "page_number": 1, "description": "Wire transfer receipt from Eleanor Vance for $8,500", "verified": True}
            ]
        },
        {
            "id": "COND-PTD-02",
            "loan_id": "L-20417",
            "category": "PTD",
            "code": "PTD-02",
            "title": "Recent Paystub Verification",
            "description": "Provide most recent 30-day paystub reflecting year-to-date earnings for Acme Corp.",
            "cited_rule": "Fannie Mae Selling Guide B3-3.1-01",
            "status": "open",
            "owner": "borrower",
            "evidence": [
                {"doc_id": "DOC-PAYSTUB-01", "page_number": 1, "description": "Paystub dated 2026-01-31 from Acme Corp", "verified": True}
            ]
        }
    ]

    for c in conditions:
        evs = c.pop("evidence")
        if db.use_supabase:
            db.supabase.table("conditions").upsert(c).execute()
            for ev in evs:
                ev_id = f"EV-{c['id']}-{ev['doc_id']}"
                db.supabase.table("condition_evidence").upsert({
                    "id": ev_id,
                    "condition_id": c["id"],
                    "doc_id": ev["doc_id"],
                    "page_number": ev["page_number"],
                    "description": ev["description"],
                    "verified": ev["verified"],
                    "created_at": now
                }).execute()
        else:
            conn = db._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO conditions (id, loan_id, category, code, title, description, cited_rule, status, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (c["id"], c["loan_id"], c["category"], c["code"], c["title"], c["description"], c["cited_rule"], c["status"], c["owner"], now)
            )
            for ev in evs:
                ev_id = f"EV-{c['id']}-{ev['doc_id']}"
                conn.execute(
                    "INSERT OR REPLACE INTO condition_evidence (id, condition_id, doc_id, page_number, description, verified, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ev_id, c["id"], ev["doc_id"], ev["page_number"], ev["description"], 1 if ev["verified"] else 0, now)
                )
            conn.commit()
            conn.close()

    # 5. URLA Staged & Committed Data
    urla_sections = [
        ("section_1_borrower", {"name": "John Doe", "email": "john.doe@example.com", "ssn_last4": "4819"}, {}),
        ("section_2_financial", {"employer": "Acme Corp", "monthly_income": 6000.00, "position": "Senior Engineer"}, {}),
        ("section_5_declarations", {"outstanding_judgments": False, "declared_bankruptcy": False, "party_to_lawsuit": False}, {})
    ]

    for sec_name, comm_data, staged_data in urla_sections:
        if db.use_supabase:
            db.supabase.table("urla_data").upsert({
                "id": f"URLA-L20417-{sec_name}",
                "loan_id": "L-20417",
                "section_name": sec_name,
                "committed_data": comm_data,
                "staged_data": staged_data,
                "created_at": now
            }).execute()
        else:
            conn = db._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO urla_data (id, loan_id, section_name, committed_data, staged_data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"URLA-L20417-{sec_name}", "L-20417", sec_name, json.dumps(comm_data), json.dumps(staged_data), now)
            )
            conn.commit()
            conn.close()

    print("Synthetic loan data seeded successfully for Loan L-20417.")

if __name__ == "__main__":
    seed_database()
