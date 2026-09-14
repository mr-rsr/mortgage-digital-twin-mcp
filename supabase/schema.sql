-- Mortgage Digital Twin Relational & Audit Schema
-- Conforms to Fannie Mae LL-2026-04 and Freddie Mac Bulletin 2025-16 AI Governance

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Loans Table
CREATE TABLE IF NOT EXISTS loans (
    id TEXT PRIMARY KEY,
    borrower_name TEXT NOT NULL,
    property_address TEXT NOT NULL,
    program TEXT NOT NULL, -- 'conv_30_fixed', 'fha_30_fixed', etc.
    purpose TEXT NOT NULL, -- 'purchase', 'refinance'
    occupancy TEXT NOT NULL, -- 'primary', 'secondary', 'investment'
    loan_amount NUMERIC(12,2) NOT NULL,
    interest_rate NUMERIC(5,3) NOT NULL,
    milestone TEXT NOT NULL DEFAULT 'application',
    lock_status TEXT NOT NULL DEFAULT 'unlocked', -- 'locked', 'unlocked', 'expired'
    locked_at TIMESTAMPTZ,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Loan Documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    loan_id TEXT REFERENCES loans(id),
    type TEXT NOT NULL, -- 'paystub', 'w2', 'bank_statement', 'tax_return', 'gift_letter', 'transfer_receipt', 'title_fee_sheet', etc.
    borrower_name TEXT NOT NULL,
    page_count INT NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'indexed', -- 'indexed', 'split', 'verified'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Disclosures (LE and CD)
CREATE TABLE IF NOT EXISTS disclosures (
    id TEXT PRIMARY KEY,
    loan_id TEXT REFERENCES loans(id),
    type TEXT NOT NULL, -- 'LE', 'CD'
    version INT NOT NULL,
    issued_date DATE NOT NULL,
    received_date DATE,
    receipt_method TEXT, -- 'e_ack', 'mail_presumed', 'hand_delivered'
    apr NUMERIC(6,3) NOT NULL,
    loan_product TEXT NOT NULL,
    prepay_penalty BOOLEAN NOT NULL DEFAULT FALSE,
    lender_credits NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    baseline_ref TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Disclosure Fees
CREATE TABLE IF NOT EXISTS fees (
    id TEXT PRIMARY KEY,
    disclosure_id TEXT REFERENCES disclosures(id),
    code TEXT NOT NULL, -- 'origination', 'appraisal', 'title_lenders_policy', 'settlement_fee', 'recording', etc.
    label TEXT NOT NULL,
    section TEXT NOT NULL, -- 'A', 'B', 'C', 'E', 'F', 'G', 'H', 'J'
    amount NUMERIC(10,2) NOT NULL,
    payee TEXT,
    payee_affiliated BOOLEAN NOT NULL DEFAULT FALSE,
    borrower_shopped BOOLEAN NOT NULL DEFAULT FALSE,
    on_spl BOOLEAN NOT NULL DEFAULT FALSE,
    baseline_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Changed Circumstance (COC) Events
CREATE TABLE IF NOT EXISTS coc_events (
    id TEXT PRIMARY KEY,
    loan_id TEXT REFERENCES loans(id),
    occurred_at TIMESTAMPTZ NOT NULL,
    known_at TIMESTAMPTZ NOT NULL,
    reason_code TEXT NOT NULL, -- 'rate_lock', 'extraordinary_event', 'inaccurate_info', 'borrower_requested'
    description TEXT NOT NULL,
    fees_affected JSONB DEFAULT '[]'::jsonb,
    revised_le_id TEXT,
    status TEXT NOT NULL DEFAULT 'approved', -- 'approved', 'rejected', 'review'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Underwriting Conditions
CREATE TABLE IF NOT EXISTS conditions (
    id TEXT PRIMARY KEY,
    loan_id TEXT REFERENCES loans(id),
    category TEXT NOT NULL, -- 'PTD' (Prior to Doc), 'PTF' (Prior to Funding)
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    cited_rule TEXT NOT NULL, -- e.g. 'Fannie Mae Selling Guide B3-4.2-02'
    status TEXT NOT NULL DEFAULT 'open', -- 'open', 'docs_requested', 'ready_for_review', 'submitted', 'cleared', 'waived'
    owner TEXT NOT NULL DEFAULT 'borrower',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Condition Evidence Links
CREATE TABLE IF NOT EXISTS condition_evidence (
    id TEXT PRIMARY KEY,
    condition_id TEXT REFERENCES conditions(id),
    doc_id TEXT REFERENCES documents(id),
    page_number INT NOT NULL DEFAULT 1,
    description TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. URLA Staged & Committed Form 1003 Data
CREATE TABLE IF NOT EXISTS urla_data (
    id TEXT PRIMARY KEY,
    loan_id TEXT REFERENCES loans(id),
    section_name TEXT NOT NULL, -- 'section_1_borrower', 'section_2_financial', 'section_3_real_estate', 'section_4_loan', 'section_5_declarations'
    committed_data JSONB DEFAULT '{}'::jsonb,
    staged_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Append-Only Agent Reasoning Trace (Fannie/Freddie Audit Trail)
CREATE TABLE IF NOT EXISTS agent_trace (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    decision_payload JSONB NOT NULL,
    confidence NUMERIC(4,3) NOT NULL,
    evidence_refs JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Policy Violations Register
CREATE TABLE IF NOT EXISTS policy_violations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    rule_violated TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Human Escalations Queue
CREATE TABLE IF NOT EXISTS escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'queued_for_review',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Borrower Communications
CREATE TABLE IF NOT EXISTS borrower_comms (
    id TEXT PRIMARY KEY,
    loan_id TEXT REFERENCES loans(id),
    request_type TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent', -- 'sent', 'acknowledged', 'reminded', 'overdue'
    due_date DATE NOT NULL,
    reminder_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fast Indexes
CREATE INDEX IF NOT EXISTS idx_docs_loan_id ON documents (loan_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_loan_id ON disclosures (loan_id);
CREATE INDEX IF NOT EXISTS idx_fees_disclosure_id ON fees (disclosure_id);
CREATE INDEX IF NOT EXISTS idx_conditions_loan_id ON conditions (loan_id);
CREATE INDEX IF NOT EXISTS idx_trace_entity_id ON agent_trace (entity_id);
CREATE INDEX IF NOT EXISTS idx_trace_created_at ON agent_trace (created_at);
CREATE INDEX IF NOT EXISTS idx_violations_entity ON policy_violations (entity_id);
