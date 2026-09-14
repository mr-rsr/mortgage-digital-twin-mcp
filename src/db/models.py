from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Loan(BaseModel):
    id: str
    borrower_name: str
    property_address: str
    program: str = "conv_30_fixed"
    purpose: str = "purchase"
    occupancy: str = "primary"
    loan_amount: float
    interest_rate: float
    milestone: str = "application"
    lock_status: str = "unlocked"
    locked_at: Optional[str] = None
    version: int = 1

class Document(BaseModel):
    id: str
    loan_id: str
    type: str
    borrower_name: str
    page_count: int = 1
    status: str = "indexed"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FeeItem(BaseModel):
    code: str
    label: str
    section: str # A, B, C, E, F, G, H, J
    amount: float
    payee: Optional[str] = None
    payee_affiliated: bool = False
    borrower_shopped: bool = False
    on_spl: bool = False
    baseline_amount: float = 0.0

class Disclosure(BaseModel):
    id: str
    loan_id: str
    type: str # LE or CD
    version: int
    issued_date: str # YYYY-MM-DD
    received_date: Optional[str] = None
    receipt_method: Optional[str] = "e_ack"
    apr: float
    loan_product: str = "conv_30_fixed"
    prepay_penalty: bool = False
    lender_credits: float = 0.0
    baseline_ref: Optional[str] = None
    fees: List[FeeItem] = Field(default_factory=list)

class COCEvent(BaseModel):
    id: str
    loan_id: str
    occurred_at: str
    known_at: str
    reason_code: str
    description: str
    fees_affected: List[str] = Field(default_factory=list)
    revised_le_id: Optional[str] = None
    status: str = "approved"

class Condition(BaseModel):
    id: str
    loan_id: str
    category: str # PTD or PTF
    code: str
    title: str
    description: str
    cited_rule: str
    status: str = "open" # open, docs_requested, ready_for_review, submitted, cleared, waived
    owner: str = "borrower"
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

class StagedChange(BaseModel):
    field_id: str
    current_value: Any
    staged_value: Any
    evidence_doc_id: Optional[str] = None
    status: str = "staged"
