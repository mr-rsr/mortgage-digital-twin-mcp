from typing import Any, Dict, List, Optional
from src.db.client import db
from src.engines.trid_engine import TRIDEngine
from src.engines.calendar_oracle import CalendarOracle

def audit_disclosure(
    loan_id: str,
    cd_disclosure_id: str,
    target_consummation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compares Closing Disclosure against baseline Loan Estimate.
    Executes TRID 3-bucket tolerance test, APR drift check, timing rules, and outputs exact cure dollars.
    """
    cd = db.get_disclosure(cd_disclosure_id)
    if not cd:
        return {"error": f"Closing disclosure '{cd_disclosure_id}' not found."}

    # Identify baseline LE
    baseline_id = cd.get("baseline_ref")
    if not baseline_id:
        all_discs = db.get_disclosures_for_loan(loan_id)
        le_discs = [d for d in all_discs if d.get("type") == "LE"]
        if not le_discs:
            return {"error": f"No baseline Loan Estimate found for loan '{loan_id}'."}
        baseline_le = le_discs[-1]
    else:
        baseline_le = db.get_disclosure(baseline_id)

    if not baseline_le:
        return {"error": f"Baseline LE '{baseline_id}' not found."}

    coc_events = db.get_coc_events(loan_id)
    audit_res = TRIDEngine.audit_disclosures(
        le_disc=baseline_le,
        cd_disc=cd,
        target_consummation=target_consummation,
        coc_events=coc_events
    )

    # Log to shared trace
    db.write_trace(
        entity_id=loan_id,
        agent_name="TRIDDisclosureAgent",
        decision_type="trid_audit_completed",
        decision_payload={
            "cd_id": cd_disclosure_id,
            "baseline_le_id": baseline_le["id"],
            "total_cure": audit_res["tolerance"]["total_cure"],
            "route": audit_res["route"]
        },
        confidence=1.0,
        evidence_refs=[cd_disclosure_id, baseline_le["id"]]
    )

    return audit_res

def check_timing(
    cd_received_date: str,
    target_consummation: str
) -> Dict[str, Any]:
    """
    Checks the statutory 3-day CD waiting period prior to consummation using the specific calendar.
    """
    earliest = CalendarOracle.calculate_earliest_consummation(cd_received_date)
    target_d = CalendarOracle._parse_date(target_consummation)
    wait_met = (target_d >= earliest)

    return {
        "cd_received_date": cd_received_date,
        "target_consummation": target_consummation,
        "earliest_permissible_consummation": earliest.isoformat(),
        "wait_met": wait_met,
        "rule_citation": "12 CFR 1026.19(f)(1)(ii)",
        "message": "Waiting period requirement satisfied." if wait_met else f"Consummation date {target_consummation} violates 3-day wait; cannot close before {earliest.isoformat()}."
    }

def stage_cd_proposal(
    loan_id: str,
    cd_version: int,
    lender_credit_cure_amount: float,
    cure_memo: str
) -> Dict[str, Any]:
    """
    Stages a proposed Section J lender-credit tolerance cure line and memo for human closer sign-off.
    Direct sending of CD to borrower by agent is strictly refused.
    """
    proposal_id = f"PROP-CD-{loan_id}-V{cd_version}"
    trace_id = db.write_trace(
        entity_id=loan_id,
        agent_name="TRIDDisclosureAgent",
        decision_type="cd_cure_proposal_staged",
        decision_payload={
            "proposal_id": proposal_id,
            "cd_version": cd_version,
            "lender_credit_cure_amount": lender_credit_cure_amount,
            "cure_memo": cure_memo,
            "status": "pending_closer_review"
        },
        confidence=1.0,
        evidence_refs=[f"CD-V{cd_version}"]
    )

    return {
        "status": "staged_for_closer_approval",
        "proposal_id": proposal_id,
        "loan_id": loan_id,
        "lender_credit_cure_amount": lender_credit_cure_amount,
        "cure_memo": cure_memo,
        "trace_id": trace_id,
        "closer_approval_required": True,
        "direct_send_to_borrower_allowed": False
    }
