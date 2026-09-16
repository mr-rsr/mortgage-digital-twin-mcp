from typing import Any, Dict, List, Optional
from src.db.client import db
from src.engines.condition_engine import ConditionEngine

def evaluate_large_deposit(
    loan_id: str,
    condition_id: str,
    monthly_qualifying_income: float,
    deposit_amount: float,
    deposit_date: str
) -> Dict[str, Any]:
    """
    Evaluates bank statement, gift letter, and transfer receipt against Fannie Mae large-deposit guidelines.
    """
    docs = db.list_documents(loan_id)
    bank_doc = next((d for d in docs if d["type"] == "bank_statement"), None)
    gift_doc = next((d for d in docs if d["type"] == "gift_letter"), None)
    wire_doc = next((d for d in docs if d["type"] == "transfer_receipt"), None)

    eval_res = ConditionEngine.evaluate_large_deposit_condition(
        monthly_qualifying_income=monthly_qualifying_income,
        deposit_amount=deposit_amount,
        deposit_date=deposit_date,
        bank_doc=bank_doc,
        gift_doc=gift_doc,
        wire_doc=wire_doc
    )

    db.write_trace(
        entity_id=loan_id,
        agent_name="ConditionClearingAgent",
        decision_type="large_deposit_evaluated",
        decision_payload={
            "condition_id": condition_id,
            "deposit_amount": deposit_amount,
            "eval_status": eval_res["status"],
            "ready_for_processor_review": eval_res["ready_for_processor_review"]
        },
        confidence=0.98 if eval_res["ready_for_processor_review"] else 0.50,
        evidence_refs=[d["id"] for d in [bank_doc, gift_doc, wire_doc] if d]
    )

    return eval_res

def draft_loe(
    borrower_name: str,
    property_address: str,
    subject: str,
    explanation_body: str
) -> Dict[str, Any]:
    """
    Drafts a formal Letter of Explanation (LOE) package for borrower e-signature.
    """
    text = ConditionEngine.generate_loe_draft(
        borrower_name=borrower_name,
        property_address=property_address,
        subject=subject,
        explanation_body=explanation_body
    )
    return {
        "status": "drafted",
        "loe_text": text,
        "borrower_signature_required": True
    }

def stage_condition_package(
    loan_id: str,
    condition_id: str,
    evidence_doc_ids: List[str]
) -> Dict[str, Any]:
    """
    Assembles verified condition evidence into a package for human processor review.
    Cannot directly clear condition or submit directly to underwriting without processor action.
    """
    conditions = db.list_conditions(loan_id)
    cond = next((c for c in conditions if c["id"] == condition_id), None)
    if not cond:
        return {"error": f"Condition '{condition_id}' not found."}

    docs = db.list_documents(loan_id)
    matched_docs = [d for d in docs if d["id"] in evidence_doc_ids]

    cover_sheet = ConditionEngine.assemble_package_cover_sheet(
        condition=cond,
        evidence_items=[{"doc_id": d["id"], "page_number": 1, "description": d["type"]} for d in matched_docs],
        agent_name="ConditionClearingAgent"
    )

    db.write_trace(
        entity_id=loan_id,
        agent_name="ConditionClearingAgent",
        decision_type="condition_package_staged",
        decision_payload={
            "condition_id": condition_id,
            "evidence_count": len(matched_docs),
            "recommendation": "ready_for_processor_review"
        },
        confidence=0.95,
        evidence_refs=evidence_doc_ids
    )

    # Update status to ready_for_review
    db.update_condition_status(condition_id, status="ready_for_review")

    return {
        "status": "staged_for_processor_review",
        "cover_sheet": cover_sheet,
        "condition_id": condition_id,
        "evidence_doc_ids": evidence_doc_ids,
        "underwriter_submission_allowed": False,
        "message": "Package staged. Processor review and manual sign-off required prior to underwriter submission."
    }

def update_condition(
    loan_id: str,
    condition_id: str,
    target_status: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates condition status within allowed agent boundaries.
    REFUSES 'cleared', 'waived', or 'submitted' actions with FORBIDDEN_ROLE and logs a policy violation.
    """
    forbidden_statuses = {"cleared", "waived", "submitted"}
    status_clean = target_status.lower().strip()

    if status_clean in forbidden_statuses:
        violation_id = db.record_policy_violation(
            entity_id=loan_id,
            agent_name="ConditionClearingAgent",
            tool_name="update_condition",
            rule_violated="FORBIDDEN_ROLE",
            detail=f"Agent attempted to set condition '{condition_id}' to status '{target_status}'. Only human underwriter/processor may clear, waive, or submit conditions."
        )
        return {
            "isError": True,
            "code": "FORBIDDEN_ROLE",
            "violation_id": violation_id,
            "message": f"Action refused: Agents cannot transition condition to '{target_status}'. Human review required.",
            "retryable": False
        }

    db.update_condition_status(condition_id, status=status_clean, notes=notes)
    return {
        "status": "updated",
        "condition_id": condition_id,
        "current_status": status_clean,
        "notes": notes
    }
