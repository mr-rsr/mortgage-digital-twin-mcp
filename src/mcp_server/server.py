"""
Mortgage Multi-Agent FastMCP Server
Exposes tools for A1 (Loan Set-up & Intake), A2 (Condition Clearing),
A3 (TRID CD vs LE Review), Production LOS queries, Comms, and Shared Governance Trace.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from typing import Any, Dict, List, Optional
from fastmcp import FastMCP

from src.mcp_server.tools import trace, trid, conditions, setup, los, comms

# Initialize FastMCP Server
mcp = FastMCP("Mortgage Multi-Agent Digital Twin Server")


# -------------------------------------------------------------
# 1. Shared Trace & Governance Tools (trace.*)
# -------------------------------------------------------------
@mcp.tool(name="trace_write_decision")
def trace_write_decision(
    entity_id: str,
    agent_name: str,
    decision_type: str,
    decision_payload: Dict[str, Any],
    confidence: float,
    evidence_refs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Every agent calls this after making a decision to write to the shared append-only trace."""
    return trace.write_decision(
        entity_id=entity_id,
        agent_name=agent_name,
        decision_type=decision_type,
        decision_payload=decision_payload,
        confidence=confidence,
        evidence_refs=evidence_refs
    )


@mcp.tool(name="trace_query")
def trace_query(entity_id: str) -> Dict[str, Any]:
    """Pull the full chronological decision trace history for an entity across all agents."""
    return trace.query(entity_id=entity_id)


@mcp.tool(name="trace_escalate_to_human")
def trace_escalate_to_human(
    entity_id: str,
    agent_name: str,
    reason: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Any agent calls this when confidence is below threshold, conflict occurs, or exception is caught."""
    return trace.escalate_to_human(
        entity_id=entity_id,
        agent_name=agent_name,
        reason=reason,
        context=context
    )


# -------------------------------------------------------------
# 2. TRID & Closing Disclosure Agent Tools (trid.*)
# -------------------------------------------------------------
@mcp.tool(name="trid_audit_disclosure")
def trid_audit_disclosure(
    loan_id: str,
    cd_disclosure_id: str,
    target_consummation: Optional[str] = None
) -> Dict[str, Any]:
    """Run TRID 3-bucket tolerance audit (0%, 10%, no-limit), calculate exact cure dollars, APR drift, and timing."""
    return trid.audit_disclosure(
        loan_id=loan_id,
        cd_disclosure_id=cd_disclosure_id,
        target_consummation=target_consummation
    )


@mcp.tool(name="trid_check_timing")
def trid_check_timing(
    cd_received_date: str,
    target_consummation: str
) -> Dict[str, Any]:
    """Verify statutory 3-day CD waiting period prior to consummation using the specific calendar (excluding Sundays and holidays)."""
    return trid.check_timing(
        cd_received_date=cd_received_date,
        target_consummation=target_consummation
    )


@mcp.tool(name="los_stage_cd_proposal")
def los_stage_cd_proposal(
    loan_id: str,
    cd_version: int,
    lender_credit_cure_amount: float,
    cure_memo: str
) -> Dict[str, Any]:
    """Stage a proposed Section J lender-credit tolerance cure line and memo for human closer approval."""
    return trid.stage_cd_proposal(
        loan_id=loan_id,
        cd_version=cd_version,
        lender_credit_cure_amount=lender_credit_cure_amount,
        cure_memo=cure_memo
    )


# -------------------------------------------------------------
# 3. Condition Clearing Agent Tools (condition.*)
# -------------------------------------------------------------
@mcp.tool(name="condition_evaluate_large_deposit")
def condition_evaluate_large_deposit(
    loan_id: str,
    condition_id: str,
    monthly_qualifying_income: float,
    deposit_amount: float,
    deposit_date: str
) -> Dict[str, Any]:
    """Evaluate bank statement, gift letter, and transfer receipt against Fannie Mae B3-4.2-02 large deposit rule."""
    return conditions.evaluate_large_deposit(
        loan_id=loan_id,
        condition_id=condition_id,
        monthly_qualifying_income=monthly_qualifying_income,
        deposit_amount=deposit_amount,
        deposit_date=deposit_date
    )


@mcp.tool(name="condition_draft_loe")
def condition_draft_loe(
    borrower_name: str,
    property_address: str,
    subject: str,
    explanation_body: str
) -> Dict[str, Any]:
    """Generate a formal Letter of Explanation (LOE) package for borrower e-signature."""
    return conditions.draft_loe(
        borrower_name=borrower_name,
        property_address=property_address,
        subject=subject,
        explanation_body=explanation_body
    )


@mcp.tool(name="los_stage_condition_package")
def los_stage_condition_package(
    loan_id: str,
    condition_id: str,
    evidence_doc_ids: List[str]
) -> Dict[str, Any]:
    """Assemble verified evidence cover sheet and stage package for human processor sign-off."""
    return conditions.stage_condition_package(
        loan_id=loan_id,
        condition_id=condition_id,
        evidence_doc_ids=evidence_doc_ids
    )


@mcp.tool(name="los_update_condition")
def los_update_condition(
    loan_id: str,
    condition_id: str,
    target_status: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Update condition notes/status. Refuses 'cleared' or 'submitted' with FORBIDDEN_ROLE policy violation."""
    return conditions.update_condition(
        loan_id=loan_id,
        condition_id=condition_id,
        target_status=target_status,
        notes=notes
    )


# -------------------------------------------------------------
# 4. Loan Set-up & Intake Agent Tools (setup.*)
# -------------------------------------------------------------
@mcp.tool(name="setup_calculate_income")
def setup_calculate_income(
    income_type: str,
    amount: float,
    frequency: Optional[str] = "monthly",
    hours_per_week: Optional[float] = 40.0,
    prior_year_amount: Optional[float] = None,
    ytd_amount: Optional[float] = None,
    ytd_months: Optional[float] = None
) -> Dict[str, Any]:
    """Compute qualifying income per Fannie Mae Form 1084 (base salary, hourly, or variable overtime/bonus)."""
    return setup.calculate_income(
        income_type=income_type,
        amount=amount,
        frequency=frequency,
        hours_per_week=hours_per_week,
        prior_year_amount=prior_year_amount,
        ytd_amount=ytd_amount,
        ytd_months=ytd_months
    )


@mcp.tool(name="setup_check_large_deposits")
def setup_check_large_deposits(
    loan_id: str,
    monthly_qualifying_income: float
) -> Dict[str, Any]:
    """Scan loan bank statements for deposits exceeding 50% of monthly qualifying income per Fannie Mae B3-4.2-02."""
    return setup.check_large_deposits(
        loan_id=loan_id,
        monthly_qualifying_income=monthly_qualifying_income
    )


@mcp.tool(name="setup_generate_needs_list")
def setup_generate_needs_list(loan_id: str) -> Dict[str, Any]:
    """Audit indexed documents against loan program requirements and generate an itemized borrower needs list."""
    return setup.generate_needs_list(loan_id=loan_id)


@mcp.tool(name="los_stage_fields")
def los_stage_fields(
    loan_id: str,
    section_name: str,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Stage proposed URLA Form 1003 fields. Rejects Sections 5-8 with FORBIDDEN_ATTESTATION policy violation."""
    return setup.stage_fields(
        loan_id=loan_id,
        section_name=section_name,
        fields=fields
    )


# -------------------------------------------------------------
# 5. Production LOS Query Tools (los.*)
# -------------------------------------------------------------
@mcp.tool(name="los_get_loan")
def los_get_loan(loan_id: str) -> Dict[str, Any]:
    """Retrieve loan summary, milestone, lock status, interest rate, and version."""
    return los.get_loan(loan_id=loan_id)


@mcp.tool(name="los_list_documents")
def los_list_documents(loan_id: str) -> Dict[str, Any]:
    """List indexed loan documents, page counts, and metadata."""
    return los.list_documents(loan_id=loan_id)


@mcp.tool(name="los_get_urla")
def los_get_urla(loan_id: str) -> Dict[str, Any]:
    """Retrieve committed and staged URLA 1003 sections side-by-side."""
    return los.get_urla(loan_id=loan_id)


@mcp.tool(name="los_list_conditions")
def los_list_conditions(loan_id: str) -> Dict[str, Any]:
    """List all underwriting conditions with category (PTD/PTF), cited rule, and evidence."""
    return los.list_conditions(loan_id=loan_id)


@mcp.tool(name="los_list_disclosures")
def los_list_disclosures(loan_id: str) -> Dict[str, Any]:
    """List all Loan Estimates and Closing Disclosures with fee items."""
    return los.list_disclosures(loan_id=loan_id)


# -------------------------------------------------------------
# 6. Communication Surface Tools (comms.*)
# -------------------------------------------------------------
@mcp.tool(name="comms_send_borrower_request")
def comms_send_borrower_request(
    loan_id: str,
    request_type: str,
    message: str,
    due_date: str
) -> Dict[str, Any]:
    """Send an itemized documentation request to the borrower with a due date."""
    return comms.send_borrower_request(
        loan_id=loan_id,
        request_type=request_type,
        message=message,
        due_date=due_date
    )


@mcp.tool(name="comms_get_thread")
def comms_get_thread(loan_id: str) -> Dict[str, Any]:
    """Retrieve all borrower communications, reminders, and delivery statuses."""
    return comms.get_thread(loan_id=loan_id)


if __name__ == "__main__":
    import argparse
    from src.config import settings

    parser = argparse.ArgumentParser(description="Run Mortgage Multi-Agent FastMCP Server")
    parser.add_argument("--transport", choices=["sse", "stdio", "http"], default="sse", help="Transport mode")
    parser.add_argument("--host", default=settings.mcp_server_host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.mcp_server_port, help="Port to bind to")
    args = parser.parse_args()

    print(f"Starting Mortgage FastMCP Server with transport='{args.transport}' on {args.host}:{args.port}...")
    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")
