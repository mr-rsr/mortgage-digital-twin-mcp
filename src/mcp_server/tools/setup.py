from typing import Any, Dict, List, Optional
from src.db.client import db
from src.engines.income_engine import IncomeEngine

def calculate_income(
    income_type: str,
    amount: float,
    frequency: Optional[str] = "monthly",
    hours_per_week: Optional[float] = 40.0,
    prior_year_amount: Optional[float] = None,
    ytd_amount: Optional[float] = None,
    ytd_months: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes deterministic monthly qualifying income according to Fannie Mae Form 1084 rules.
    Supported types: 'base_salary', 'hourly', 'variable_overtime_bonus'.
    """
    itype = income_type.lower()
    if itype in ["salary", "base_salary"]:
        return IncomeEngine.calculate_base_salary(amount=amount, frequency=frequency or "monthly")
    elif itype == "hourly":
        return IncomeEngine.calculate_hourly_income(hourly_rate=amount, hours_per_week=hours_per_week or 40.0)
    elif itype in ["overtime", "bonus", "variable_overtime_bonus"]:
        if prior_year_amount is None or ytd_amount is None or ytd_months is None:
            return {"error": "prior_year_amount, ytd_amount, and ytd_months are required for variable income calculation."}
        return IncomeEngine.calculate_overtime_or_bonus(
            prior_year_amount=prior_year_amount,
            current_year_ytd_amount=ytd_amount,
            ytd_months=ytd_months
        )
    else:
        return {"error": f"Unknown income_type: '{income_type}'. Use 'base_salary', 'hourly', or 'overtime'."}

def check_large_deposits(loan_id: str, monthly_qualifying_income: float) -> Dict[str, Any]:
    """
    Scans loan bank statements for large deposits exceeding 50% of monthly qualifying income (Fannie B3-4.2-02).
    """
    docs = db.list_documents(loan_id)
    threshold = round(monthly_qualifying_income * 0.50, 2)
    flagged = []

    for d in docs:
        if d["type"] == "bank_statement":
            meta = d.get("metadata", {})
            deposits = meta.get("large_deposits", [])
            for dep in deposits:
                amt = float(dep.get("amount", 0.0))
                if amt > threshold:
                    flagged.append({
                        "doc_id": d["id"],
                        "date": dep.get("date"),
                        "amount": amt,
                        "description": dep.get("description"),
                        "threshold_50_pct": threshold,
                        "requires_sourcing": True
                    })

    db.write_trace(
        entity_id=loan_id,
        agent_name="LoanSetupAgent",
        decision_type="large_deposits_scanned",
        decision_payload={
            "monthly_income": monthly_qualifying_income,
            "threshold": threshold,
            "flagged_count": len(flagged)
        },
        confidence=1.0,
        evidence_refs=[f["doc_id"] for f in flagged]
    )

    return {
        "loan_id": loan_id,
        "monthly_qualifying_income": monthly_qualifying_income,
        "large_deposit_threshold": threshold,
        "flagged_deposits": flagged,
        "count": len(flagged),
        "rule_citation": "Fannie Mae Selling Guide B3-4.2-02"
    }

def generate_needs_list(loan_id: str) -> Dict[str, Any]:
    """
    Cross-checks indexed document stack against loan program requirements and generates an itemized needs list.
    """
    loan = db.get_loan(loan_id)
    if not loan:
        return {"error": f"Loan '{loan_id}' not found."}

    docs = db.list_documents(loan_id)
    doc_types = [d["type"] for d in docs]
    program = loan.get("program", "conv_30_fixed")

    missing = IncomeEngine.generate_needs_list(program=program, indexed_document_types=doc_types)

    return {
        "loan_id": loan_id,
        "program": program,
        "indexed_types": doc_types,
        "missing_documents": missing,
        "missing_count": len(missing)
    }

def stage_fields(
    loan_id: str,
    section_name: str,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Proposes URLA (Form 1003) field values for loan officer review.
    STRICTLY REFUSES Sections 5 (Declarations), 6, 7, 8 with FORBIDDEN_ATTESTATION and logs a policy violation.
    """
    try:
        IncomeEngine.validate_urla_field_staging(section_name=section_name, field_name="")
    except PermissionError as e:
        violation_id = db.record_policy_violation(
            entity_id=loan_id,
            agent_name="LoanSetupAgent",
            tool_name="stage_fields",
            rule_violated="FORBIDDEN_ATTESTATION",
            detail=str(e)
        )
        return {
            "isError": True,
            "code": "FORBIDDEN_ATTESTATION",
            "violation_id": violation_id,
            "message": str(e),
            "retryable": False
        }

    db.stage_urla_fields(loan_id=loan_id, section_name=section_name, staged_fields=fields)
    db.write_trace(
        entity_id=loan_id,
        agent_name="LoanSetupAgent",
        decision_type="urla_fields_staged",
        decision_payload={"section": section_name, "fields": fields},
        confidence=1.0,
        evidence_refs=[]
    )

    return {
        "status": "fields_staged",
        "loan_id": loan_id,
        "section_name": section_name,
        "staged_fields": fields,
        "human_review_required": True
    }
