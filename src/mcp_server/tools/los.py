from typing import Any, Dict, List, Optional
from src.db.client import db

def get_loan(loan_id: str) -> Dict[str, Any]:
    """Retrieves loan summary, milestone, lock status, interest rate, and version."""
    loan = db.get_loan(loan_id)
    if not loan:
        return {"error": f"Loan '{loan_id}' not found."}
    return loan

def list_documents(loan_id: str) -> Dict[str, Any]:
    """Lists all indexed loan documents with page counts and metadata."""
    docs = db.list_documents(loan_id)
    return {
        "loan_id": loan_id,
        "count": len(docs),
        "documents": docs
    }

def get_urla(loan_id: str) -> Dict[str, Any]:
    """Retrieves committed and staged URLA 1003 data side-by-side."""
    urla_sections = db.get_urla_data(loan_id)
    return {
        "loan_id": loan_id,
        "sections": urla_sections
    }

def list_conditions(loan_id: str) -> Dict[str, Any]:
    """Lists all underwriting conditions with category (PTD/PTF), cited rule, and evidence."""
    conds = db.list_conditions(loan_id)
    return {
        "loan_id": loan_id,
        "count": len(conds),
        "conditions": conds
    }

def list_disclosures(loan_id: str) -> Dict[str, Any]:
    """Lists all Loan Estimates and Closing Disclosures with fee items."""
    discs = db.get_disclosures_for_loan(loan_id)
    return {
        "loan_id": loan_id,
        "count": len(discs),
        "disclosures": discs
    }
