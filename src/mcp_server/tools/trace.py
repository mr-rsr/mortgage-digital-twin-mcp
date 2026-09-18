from typing import Any, Dict, List, Optional
from src.db.client import db

def write_decision(
    entity_id: str,
    agent_name: str,
    decision_type: str,
    decision_payload: Dict[str, Any],
    confidence: float,
    evidence_refs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Appends an auditable decision record to the Fannie/Freddie compliant reasoning trace."""
    trace_id = db.write_trace(
        entity_id=entity_id,
        agent_name=agent_name,
        decision_type=decision_type,
        decision_payload=decision_payload,
        confidence=confidence,
        evidence_refs=evidence_refs
    )
    return {
        "status": "success",
        "trace_id": trace_id,
        "entity_id": entity_id,
        "agent_name": agent_name
    }

def query(entity_id: str) -> Dict[str, Any]:
    """Pulls full chronological multi-agent decision history for a loan or file entity."""
    traces = db.query_trace(entity_id)
    return {
        "entity_id": entity_id,
        "count": len(traces),
        "trace": traces
    }

def escalate_to_human(
    entity_id: str,
    agent_name: str,
    reason: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Escalates an exception, guideline conflict, or low-confidence finding to a human reviewer."""
    esc_id = db.escalate_to_human(
        entity_id=entity_id,
        agent_name=agent_name,
        reason=reason,
        context=context
    )
    return {
        "status": "queued_for_review",
        "escalation_id": esc_id,
        "entity_id": entity_id,
        "agent_name": agent_name,
        "message": f"Escalated to human supervisor: {reason}"
    }
