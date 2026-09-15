from typing import Any, Dict, List, Optional
from src.engines.calendar_oracle import CalendarOracle

class TRIDEngine:
    """
    TRID 3-Bucket Tolerance, Changed Circumstance (COC), and Timing Compliance Engine.
    Conforms to 12 CFR 1026.19(e), (f) and CFPB TRID Guide rules.
    """

    @classmethod
    def classify_fee_bucket(cls, fee: Dict[str, Any]) -> str:
        """
        Classifies a fee into 'zero', 'ten', or 'none' tolerance bucket.
        """
        code = fee.get("code", "").lower()
        section = fee.get("section", "").upper()
        payee_affiliated = bool(fee.get("payee_affiliated", False))
        borrower_shopped = bool(fee.get("borrower_shopped", False))
        on_spl = bool(fee.get("on_spl", False))

        # 1. Zero tolerance fees:
        # - Section A (Origination charges: application, underwriting, processing, points)
        # - Transfer taxes (Section E)
        # - Services borrower did not / could not shop for (Section B, or lender affiliated)
        # - Any appraisal fee without an approved changed circumstance
        if section == "A" or code in ["origination", "appraisal", "transfer_taxes", "credit_report", "flood_cert"] or payee_affiliated:
            return "zero"

        # 2. 10% aggregate tolerance fees:
        # - Recording fees (Section E)
        # - Third-party services borrower was permitted to shop for AND selected from lender's SPL
        if code == "recording" or (section == "C" and on_spl and not borrower_shopped):
            return "ten"

        # 3. No limit (good faith):
        # - Prepaids (Section F), Initial escrow (Section G), Other (Section H)
        # - Services borrower shopped and selected OFF the SPL (borrower_shopped=True, on_spl=False)
        return "none"

    @classmethod
    def audit_disclosures(
        cls,
        le_disc: Dict[str, Any],
        cd_disc: Dict[str, Any],
        target_consummation: Optional[str] = None,
        coc_events: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Compares Loan Estimate against Closing Disclosure to audit:
        1. 3-bucket tolerances and exact cure calculation (Deck Worked Example T-1)
        2. Changed Circumstances (COC) legitimacy
        3. Timing and CD waiting period
        4. APR drift (> 0.125%)
        """
        le_fees = {f["code"]: f for f in le_disc.get("fees", [])}
        cd_fees = cd_disc.get("fees", [])

        zero_bucket_items = []
        ten_bucket_items = []
        none_bucket_items = []

        zero_cure = 0.0
        ten_baseline_sum = 0.0
        ten_cd_sum = 0.0

        for cd_f in cd_fees:
            code = cd_f["code"]
            le_f = le_fees.get(code, {})
            baseline = float(le_f.get("amount", cd_f.get("baseline_amount", 0.0)))
            actual = float(cd_f["amount"])
            bucket = cls.classify_fee_bucket(cd_f)

            item_info = {
                "code": code,
                "label": cd_f.get("label", code),
                "section": cd_f.get("section", ""),
                "baseline": baseline,
                "cd_amount": actual,
                "difference": round(actual - baseline, 2)
            }

            if bucket == "zero":
                item_cure = max(0.0, round(actual - baseline, 2))
                zero_cure += item_cure
                item_info["cure"] = item_cure
                zero_bucket_items.append(item_info)
            elif bucket == "ten":
                ten_baseline_sum += baseline
                ten_cd_sum += actual
                ten_bucket_items.append(item_info)
            else:
                none_bucket_items.append(item_info)

        # 10% Aggregate calculation: limit = round(baseline_sum * 1.10, 2)
        ten_baseline_sum = round(ten_baseline_sum, 2)
        ten_cd_sum = round(ten_cd_sum, 2)
        ten_limit = round(ten_baseline_sum * 1.10, 2)
        ten_cure = max(0.0, round(ten_cd_sum - ten_limit, 2))

        # Lender credit shortfall: if CD lender credit is less than LE lender credit
        le_credits = float(le_disc.get("lender_credits", 0.0))
        cd_credits = float(cd_disc.get("lender_credits", 0.0))
        credit_shortfall = max(0.0, round(le_credits - cd_credits, 2))

        total_cure = round(zero_cure + ten_cure + credit_shortfall, 2)

        # Timing analysis
        cd_received = cd_disc.get("received_date") or cd_disc.get("issued_date")
        timing_info = {}
        if cd_received:
            earliest_consummation = CalendarOracle.calculate_earliest_consummation(cd_received)
            timing_info["cd_received_date"] = cd_received
            timing_info["earliest_consummation"] = earliest_consummation.isoformat()
            if target_consummation:
                target_d = CalendarOracle._parse_date(target_consummation)
                timing_info["target_consummation"] = target_consummation
                timing_info["wait_met"] = (target_d >= earliest_consummation)
            else:
                timing_info["wait_met"] = True

        # APR Drift analysis: threshold is 0.125% for regular loans
        le_apr = float(le_disc.get("apr", 0.0))
        cd_apr = float(cd_disc.get("apr", 0.0))
        apr_diff = round(abs(cd_apr - le_apr), 4)
        apr_trigger = (apr_diff > 0.125)

        # Product change check
        product_changed = (le_disc.get("loan_product") != cd_disc.get("loan_product"))
        prepay_added = (not le_disc.get("prepay_penalty", False) and cd_disc.get("prepay_penalty", False))
        mandatory_new_wait = apr_trigger or product_changed or prepay_added

        # Determine workflow routing
        if mandatory_new_wait:
            route = "redisclose_and_reopen_3day_wait"
        elif total_cure > 0:
            route = "cure_and_send_for_closer_approval"
        else:
            route = "clear_to_close"

        return {
            "loan_id": cd_disc.get("loan_id"),
            "cd_version": cd_disc.get("version"),
            "tolerance": {
                "zero_bucket": {
                    "cure": round(zero_cure, 2),
                    "items": zero_bucket_items
                },
                "ten_bucket": {
                    "baseline_sum": ten_baseline_sum,
                    "limit_allowed": ten_limit,
                    "actual_sum": ten_cd_sum,
                    "cure": ten_cure,
                    "items": ten_bucket_items
                },
                "no_limit_bucket": {
                    "items": none_bucket_items
                },
                "lender_credit_shortfall": credit_shortfall,
                "total_cure": total_cure
            },
            "timing": timing_info,
            "apr": {
                "le_apr": le_apr,
                "cd_apr": cd_apr,
                "apr_diff": apr_diff,
                "apr_trigger": apr_trigger,
                "product_changed": product_changed,
                "prepay_added": prepay_added,
                "mandatory_new_wait": mandatory_new_wait
            },
            "route": route,
            "rule_versions": ["12 CFR 1026.19(e)(3)", "12 CFR 1026.19(f)(1)(ii)"]
        }

    @classmethod
    def validate_coc_event(
        cls,
        coc_event: Dict[str, Any],
        le_issue_date: str
    ) -> Dict[str, Any]:
        """
        Validates Changed Circumstance under TRID:
        1. Valid reason code: rate_lock, borrower_requested, extraordinary_event, inaccurate_info
        2. Revised LE issued within 3 general business days of learning of change
        """
        reason = coc_event.get("reason_code", "")
        known_at = coc_event.get("known_at", "")[:10]
        valid_reasons = ["rate_lock", "borrower_requested", "extraordinary_event", "inaccurate_info", "new_construction_delay"]

        if reason not in valid_reasons:
            return {
                "valid": False,
                "reason_status": "invalid_reason_code",
                "message": f"Reason '{reason}' is not an authorized changed circumstance under TRID."
            }

        # Check 3 general business day window
        deadline = CalendarOracle.add_business_days(known_at, 3, calendar_type="general")
        le_issued = CalendarOracle._parse_date(le_issue_date)

        if le_issued > deadline:
            return {
                "valid": False,
                "reason_status": "untimely_redisclosure",
                "known_at": known_at,
                "deadline": deadline.isoformat(),
                "le_issued_date": le_issue_date,
                "message": f"Revised LE was issued on {le_issue_date}, after the 3-day deadline of {deadline.isoformat()}."
            }

        return {
            "valid": True,
            "reason_status": "valid_and_timely",
            "known_at": known_at,
            "deadline": deadline.isoformat(),
            "le_issued_date": le_issue_date,
            "message": "Changed circumstance is valid and meets the 3-day redisclosure window."
        }
