from src.engines.trid_engine import TRIDEngine

def test_t1_deck_worked_example_cure_112():
    """
    Test T-1: Deck worked example fees.
    Appraisal: 550 -> 650 (Zero bucket cure = $100)
    10% bucket: Title 900 + Settlement 600 + Recording 180 = 1,680 baseline.
    Limit = 1,680 * 1.10 = 1,848.
    CD amounts: 1020 + 640 + 200 = 1,860. (10% bucket cure = 1,860 - 1,848 = $12)
    Total cure = $100 + $12 = $112.00.
    """
    le_disc = {
        "id": "LE-2",
        "loan_id": "L-20417",
        "apr": 6.912,
        "loan_product": "conv_30_fixed",
        "prepay_penalty": False,
        "lender_credits": 0.00,
        "fees": [
            {"code": "origination", "section": "A", "amount": 1200.00},
            {"code": "appraisal", "section": "B", "amount": 550.00},
            {"code": "transfer_taxes", "section": "E", "amount": 2100.00},
            {"code": "title_lenders_policy", "section": "C", "amount": 900.00, "on_spl": True, "borrower_shopped": False},
            {"code": "settlement_fee", "section": "C", "amount": 600.00, "on_spl": True, "borrower_shopped": False},
            {"code": "recording", "section": "E", "amount": 180.00},
            {"code": "pest_inspection", "section": "C", "amount": 150.00, "on_spl": False, "borrower_shopped": True}
        ]
    }

    cd_disc = {
        "id": "CD-1",
        "loan_id": "L-20417",
        "version": 1,
        "issued_date": "2026-03-18",
        "received_date": "2026-03-19",
        "apr": 6.948,
        "loan_product": "conv_30_fixed",
        "prepay_penalty": False,
        "lender_credits": 0.00,
        "fees": [
            {"code": "origination", "section": "A", "amount": 1200.00},
            {"code": "appraisal", "section": "B", "amount": 650.00},
            {"code": "transfer_taxes", "section": "E", "amount": 2100.00},
            {"code": "title_lenders_policy", "section": "C", "amount": 1020.00, "on_spl": True, "borrower_shopped": False},
            {"code": "settlement_fee", "section": "C", "amount": 640.00, "on_spl": True, "borrower_shopped": False},
            {"code": "recording", "section": "E", "amount": 200.00},
            {"code": "pest_inspection", "section": "C", "amount": 175.00, "on_spl": False, "borrower_shopped": True}
        ]
    }

    res = TRIDEngine.audit_disclosures(
        le_disc=le_disc,
        cd_disc=cd_disc,
        target_consummation="2026-03-24"
    )

    tolerance = res["tolerance"]
    assert tolerance["zero_bucket"]["cure"] == 100.00
    assert tolerance["ten_bucket"]["baseline_sum"] == 1680.00
    assert tolerance["ten_bucket"]["limit_allowed"] == 1848.00
    assert tolerance["ten_bucket"]["actual_sum"] == 1860.00
    assert tolerance["ten_bucket"]["cure"] == 12.00
    assert tolerance["total_cure"] == 112.00
    assert res["timing"]["wait_met"] is True
    assert res["route"] == "cure_and_send_for_closer_approval"

def test_t6_shopped_off_spl_no_limit():
    """T-6: Borrower shopped a fee and chose off the SPL -> lands in no-limit bucket, $0 cure."""
    fee = {"code": "survey", "section": "C", "amount": 500.00, "borrower_shopped": True, "on_spl": False}
    bucket = TRIDEngine.classify_fee_bucket(fee)
    assert bucket == "none"

def test_t7_same_fee_chosen_from_spl():
    """T-7: Same fee chosen from lender's Written List of Service Providers -> lands in 10% bucket."""
    fee = {"code": "survey", "section": "C", "amount": 500.00, "borrower_shopped": False, "on_spl": True}
    bucket = TRIDEngine.classify_fee_bucket(fee)
    assert bucket == "ten"

def test_t9_lender_credit_shortfall():
    """T-9: Lender credit lower on CD than LE -> shortfall counted as cure."""
    le = {"fees": [], "lender_credits": 1000.00, "apr": 6.5, "loan_product": "conv_30_fixed"}
    cd = {"fees": [], "lender_credits": 600.00, "apr": 6.5, "loan_product": "conv_30_fixed"}
    res = TRIDEngine.audit_disclosures(le_disc=le, cd_disc=cd)
    assert res["tolerance"]["lender_credit_shortfall"] == 400.00
    assert res["tolerance"]["total_cure"] == 400.00

def test_apr_drift_trigger():
    """APR drift > 0.125% triggers mandatory new wait."""
    le = {"fees": [], "apr": 6.500, "loan_product": "conv_30_fixed"}
    cd = {"fees": [], "apr": 6.635, "loan_product": "conv_30_fixed"} # diff = 0.135% > 0.125%
    res = TRIDEngine.audit_disclosures(le_disc=le, cd_disc=cd)
    assert res["apr"]["apr_trigger"] is True
    assert res["apr"]["mandatory_new_wait"] is True
    assert res["route"] == "redisclose_and_reopen_3day_wait"
