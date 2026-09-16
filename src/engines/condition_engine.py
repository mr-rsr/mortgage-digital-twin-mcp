from typing import Any, Dict, List, Optional

class ConditionEngine:
    """
    Automated Condition Clearing Engine conforming to Fannie Mae Selling Guide B3-4.2-02.
    Evaluates evidence (bank statements, gift letters, transfer receipts) against underwriting conditions.
    """

    @classmethod
    def evaluate_large_deposit_condition(
        cls,
        monthly_qualifying_income: float,
        deposit_amount: float,
        deposit_date: str,
        bank_doc: Optional[Dict[str, Any]] = None,
        gift_doc: Optional[Dict[str, Any]] = None,
        wire_doc: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates Fannie Mae Selling Guide B3-4.2-02:
        Threshold = 50% of monthly qualifying income.
        If deposit exceeds threshold, evaluates whether gift letter and wire confirmation match.
        """
        threshold = round(monthly_qualifying_income * 0.50, 2)
        exceeds_threshold = (deposit_amount > threshold)

        if not exceeds_threshold:
            return {
                "requires_sourcing": False,
                "monthly_income": monthly_qualifying_income,
                "threshold_50_pct": threshold,
                "deposit_amount": deposit_amount,
                "status": "not_applicable",
                "message": f"Deposit ${deposit_amount:,.2f} is below 50% qualifying income threshold (${threshold:,.2f}). No sourcing required."
            }

        checks = []
        is_complete = True
        donor_name = ""
        mismatch_reasons = []

        # 1. Verify Bank Statement presence
        if bank_doc:
            checks.append({"item": "bank_statement", "verified": True, "details": "Deposit reflected on bank statement."})
        else:
            is_complete = False
            mismatch_reasons.append("Bank statement documenting deposit transaction is missing.")
            checks.append({"item": "bank_statement", "verified": False, "details": "Missing bank statement."})

        # 2. Verify Gift Letter
        if gift_doc:
            g_meta = gift_doc.get("metadata", {})
            donor_name = g_meta.get("donor_name", "").strip()
            g_amount = float(g_meta.get("gift_amount", 0.0))
            no_repay = bool(g_meta.get("no_repayment", False))

            if not no_repay:
                is_complete = False
                mismatch_reasons.append("Gift letter lacks mandatory 'no repayment required' clause.")

            if abs(g_amount - deposit_amount) > 0.01:
                is_complete = False
                mismatch_reasons.append(f"Gift letter amount (${g_amount:,.2f}) does not match deposit (${deposit_amount:,.2f}).")

            checks.append({
                "item": "gift_letter",
                "verified": (no_repay and abs(g_amount - deposit_amount) <= 0.01),
                "donor": donor_name,
                "relationship": g_meta.get("relationship", ""),
                "gift_amount": g_amount
            })
        else:
            is_complete = False
            mismatch_reasons.append("Signed gift letter is missing.")
            checks.append({"item": "gift_letter", "verified": False, "details": "Missing gift letter."})

        # 3. Verify Wire Transfer Receipt
        if wire_doc:
            w_meta = wire_doc.get("metadata", {})
            sender = w_meta.get("sender", "").strip()
            w_amount = float(w_meta.get("amount", 0.0))

            if donor_name and sender.lower() != donor_name.lower():
                is_complete = False
                mismatch_reasons.append(f"Wire sender '{sender}' does not match gift letter donor '{donor_name}'.")

            if abs(w_amount - deposit_amount) > 0.01:
                is_complete = False
                mismatch_reasons.append(f"Wire amount (${w_amount:,.2f}) does not match deposit (${deposit_amount:,.2f}).")

            checks.append({
                "item": "wire_transfer_receipt",
                "verified": (donor_name and sender.lower() == donor_name.lower() and abs(w_amount - deposit_amount) <= 0.01),
                "sender": sender,
                "wire_amount": w_amount
            })
        else:
            is_complete = False
            mismatch_reasons.append("Wire transfer receipt is missing.")
            checks.append({"item": "wire_transfer_receipt", "verified": False, "details": "Missing wire transfer receipt."})

        final_status = "evidence_complete" if is_complete else "evidence_deficient"

        return {
            "requires_sourcing": True,
            "monthly_income": monthly_qualifying_income,
            "threshold_50_pct": threshold,
            "deposit_amount": deposit_amount,
            "deposit_date": deposit_date,
            "status": final_status,
            "checks": checks,
            "mismatch_reasons": mismatch_reasons,
            "ready_for_processor_review": is_complete,
            "message": "All large deposit gift evidence verified successfully." if is_complete else f"Deficiencies detected: {'; '.join(mismatch_reasons)}"
        }

    @classmethod
    def generate_loe_draft(
        cls,
        borrower_name: str,
        property_address: str,
        subject: str,
        explanation_body: str
    ) -> str:
        """
        Drafts a formal Letter of Explanation (LOE) package ready for borrower e-signature.
        """
        return f"""LETTER OF EXPLANATION (LOE)
Date: {deposit_date if 'deposit_date' in locals() else 'Current'}
To: Underwriting Department
Re: Loan Application for {borrower_name}
Subject Property: {property_address}

Subject: {subject}

Explanation:
{explanation_body}

Borrower Certification:
I/We hereby certify that the information provided above is true and accurate to the best of my/our knowledge.

________________________________________
Borrower Signature: {borrower_name}
Date: ____________________
"""

    @classmethod
    def assemble_package_cover_sheet(
        cls,
        condition: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        agent_name: str = "ConditionAgent"
    ) -> Dict[str, Any]:
        """
        Assembles a condition submission package cover sheet for processor sign-off.
        """
        return {
            "condition_id": condition["id"],
            "code": condition["code"],
            "title": condition["title"],
            "cited_rule": condition["cited_rule"],
            "assembled_by": agent_name,
            "evidence_count": len(evidence_items),
            "evidence_citations": [
                {"doc_id": ev.get("doc_id"), "page": ev.get("page_number", 1), "description": ev.get("description")}
                for ev in evidence_items
            ],
            "recommendation": "ready_for_processor_submission",
            "processor_signoff_required": True,
            "underwriter_submission_allowed": False # Agent can never submit directly to underwriter
        }
