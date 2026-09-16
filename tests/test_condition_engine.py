from src.engines.condition_engine import ConditionEngine

def test_c1_deposit_below_50_pct_threshold():
    """C-1: Deposit below 50% qualifying income threshold requires no sourcing."""
    # Monthly income $6,000 -> 50% threshold is $3,000. Deposit is $2,000.
    res = ConditionEngine.evaluate_large_deposit_condition(
        monthly_qualifying_income=6000.00,
        deposit_amount=2000.00,
        deposit_date="2026-02-24"
    )
    assert res["requires_sourcing"] is False
    assert res["status"] == "not_applicable"

def test_c2_deposit_above_threshold_all_match():
    """C-2: Deposit above threshold ($8,500), gift letter and wire match -> evidence_complete."""
    monthly_income = 6000.00 # threshold = $3,000
    deposit_amount = 8500.00

    bank_doc = {"type": "bank_statement", "metadata": {}}
    gift_doc = {
        "type": "gift_letter",
        "metadata": {
            "donor_name": "Eleanor Vance",
            "relationship": "Mother",
            "gift_amount": 8500.00,
            "no_repayment": True
        }
    }
    wire_doc = {
        "type": "transfer_receipt",
        "metadata": {
            "sender": "Eleanor Vance",
            "amount": 8500.00
        }
    }

    res = ConditionEngine.evaluate_large_deposit_condition(
        monthly_qualifying_income=monthly_income,
        deposit_amount=deposit_amount,
        deposit_date="2026-02-24",
        bank_doc=bank_doc,
        gift_doc=gift_doc,
        wire_doc=wire_doc
    )

    assert res["requires_sourcing"] is True
    assert res["status"] == "evidence_complete"
    assert res["ready_for_processor_review"] is True
    assert len(res["mismatch_reasons"]) == 0

def test_c3_donor_name_mismatch():
    """C-3: Gift letter donor name differs from wire sender -> evidence_deficient."""
    monthly_income = 6000.00
    deposit_amount = 8500.00

    bank_doc = {"type": "bank_statement"}
    gift_doc = {
        "type": "gift_letter",
        "metadata": {
            "donor_name": "Eleanor Vance",
            "gift_amount": 8500.00,
            "no_repayment": True
        }
    }
    wire_doc = {
        "type": "transfer_receipt",
        "metadata": {
            "sender": "Robert Vance", # Mismatch!
            "amount": 8500.00
        }
    }

    res = ConditionEngine.evaluate_large_deposit_condition(
        monthly_qualifying_income=monthly_income,
        deposit_amount=deposit_amount,
        deposit_date="2026-02-24",
        bank_doc=bank_doc,
        gift_doc=gift_doc,
        wire_doc=wire_doc
    )

    assert res["status"] == "evidence_deficient"
    assert res["ready_for_processor_review"] is False
    assert any("does not match" in r for r in res["mismatch_reasons"])
