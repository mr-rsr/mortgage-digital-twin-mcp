from typing import Any, Dict, List, Optional
from src.db.client import db

def send_borrower_request(
    loan_id: str,
    request_type: str,
    message: str,
    due_date: str
) -> Dict[str, Any]:
    """Sends an itemized documentation request to the borrower with a due date."""
    comm_id = db.send_borrower_request(
        loan_id=loan_id,
        request_type=request_type,
        message=message,
        due_date=due_date
    )
    db.write_trace(
        entity_id=loan_id,
        agent_name="CommsAgent",
        decision_type="borrower_request_sent",
        decision_payload={"comm_id": comm_id, "request_type": request_type, "due_date": due_date},
        confidence=1.0,
        evidence_refs=[comm_id]
    )
    return {
        "status": "sent",
        "comm_id": comm_id,
        "loan_id": loan_id,
        "due_date": due_date,
        "message": message
    }

def get_thread(loan_id: str) -> Dict[str, Any]:
    """Retrieves all borrower communication logs, reminders, and delivery statuses."""
    items = db.list_borrower_comms(loan_id)
    return {
        "loan_id": loan_id,
        "count": len(items),
        "messages": items
    }
