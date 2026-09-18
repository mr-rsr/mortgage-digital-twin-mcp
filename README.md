# Mortgage Multi-Agent Digital Twin FastMCP Server

An AI-native multi-agent Mortgage Digital Twin MCP server implementing **Loan Set-up & Intake (A1)**, **Condition Clearing & Evidence Matching (A2)**, **TRID Closing Disclosure vs. Loan Estimate Review (A3)**, and an immutable **Shared Reasoning Trace** backed by **Supabase (PostgreSQL + pgvector)** and local SQLite fallback.

Conforms to **Fannie Mae Lender Letter LL-2026-04** and **Freddie Mac Bulletin 2025-16** AI/ML governance requirements.

---

## Architecture Overview

```
                          ┌─────────────────────────────────────────┐
                          │       Mortgage Multi-Agent System       │
                          │   (A1 Set-up / A2 Conditions / A3 TRID) │
                          └───────────────────┬─────────────────────┘
                                              │ (SSE / Stdio / HTTP)
                          ┌───────────────────▼─────────────────────┐
                          │       FastMCP Server (Port 8000)        │
                          │  trace.* | trid.* | condition.*         │
                          │  setup.* | los.*  | comms.*             │
                          └───────────────────┬─────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌──────────────────────────┐                      ┌──────────────────────────┐
        │   Supabase Relational    │                      │   Embedded SQLite Store  │
        │   (Loans, Documents,     │        (or)          │   (Local Zero-Config     │
        │    Fees, Trace Log)      │                      │    Test Fallback)        │
        └──────────────────────────┘                      └──────────────────────────┘
```

---

## 1. Supabase Database Setup

### Step 1.1: Create a Supabase Project
1. Log in to [Supabase](https://supabase.com) and create a new project.
2. Under **Project Settings -> Database**, note your **Project URL** and **API Keys** (`anon` or `service_role`).

### Step 1.2: Enable `pgvector` & Apply Schema
1. Open the **SQL Editor** in your Supabase Dashboard.
2. Copy and paste the contents of `supabase/schema.sql` and run it:
   - Enables `vector` extension (`CREATE EXTENSION IF NOT EXISTS vector;`).
   - Creates tables: `loans`, `documents`, `disclosures`, `fees`, `coc_events`, `conditions`, `condition_evidence`, `urla_data`, `agent_trace` (append-only), `policy_violations`, `escalations`, and `borrower_comms`.
   - Creates query indexes for fast pipeline filtering.

### Step 1.3: Load Seed Data

You can seed synthetic loan data using either option:

**Option A (Python Seeder Script)**:
```bash
python -m src.db.seed_data
```

**Option B (SQL Editor)**:
In the **SQL Editor**, copy and paste the contents of `supabase/seed.sql` and run it.

This seeds:
- **Loan L-20417**: 30-year fixed conventional purchase loan ($450,000, 6.875%, locked).
- **Disclosures (Deck Worked Example T-1)**: Baseline `LE-2` and `CD-1` with actual vs baseline fees for 3-bucket tolerance testing ($100 zero-bucket cure + $12 ten-percent aggregate cure = $112 total cure).
- **Indexed Documents**: Checking account bank statement with an $8,500 wire deposit, signed gift letter from Eleanor Vance, wire transfer confirmation, and 30-day paystub.
- **Conditions**: `COND-PTD-07` (large deposit sourcing) and `COND-PTD-02` (recent paystub).
- **URLA Sections**: Sections 1, 2, and 5 (Declarations).

---

## 2. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Update your `.env` file with your credentials:

```env
# Supabase Configuration (Optional - defaults to local SQLite if omitted)
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-supabase-service-role-or-anon-key>

# Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000

# Local SQLite Database Path
LOCAL_DB_PATH=mortgage_twin.db

# Optional AI / Embedding Key
OPENAI_API_KEY=
```

---

## 3. Installation

Install project dependencies:

```bash
pip install -r requirements.txt
```

---

## 4. MCP Tools Reference

### A. Shared Trace & Governance Tools (`trace.*`)
Used across all agents to maintain an append-only, auditable decision log conforming to Fannie Mae LL-2026-04 and Freddie Mac Bulletin 2025-16.

| Tool Name | Description | Key Inputs | Output |
| :--- | :--- | :--- | :--- |
| `trace_write_decision` | Appends a decision record with confidence and evidence references | `entity_id`, `agent_name`, `decision_type`, `decision_payload`, `confidence`, `evidence_refs` | `status`, `trace_id` |
| `trace_query` | Pulls chronological multi-agent decision history for a loan | `entity_id` | `count`, list of trace entries |
| `trace_escalate_to_human` | Queues a loan file for human supervisor review | `entity_id`, `agent_name`, `reason`, `context` | `escalation_id`, `status` |

### B. TRID Closing Disclosure vs. LE Tools (`trid.*`)
Enforces TRID 3-bucket tolerance limits, Changed Circumstance rules, and calendar timing.

| Tool Name | Description | Key Inputs | Output |
| :--- | :--- | :--- | :--- |
| `trid_audit_disclosure` | Compares CD vs LE, calculates 0%/10%/no-limit cures, APR drift, and route | `loan_id`, `cd_disclosure_id`, `target_consummation` | `tolerance` breakdown, `timing`, `apr`, `total_cure`, `route` |
| `trid_check_timing` | Enforces statutory 3-day CD waiting period prior to consummation | `cd_received_date`, `target_consummation` | `earliest_permissible_consummation`, `wait_met` |
| `los_stage_cd_proposal` | Stages Section J lender-credit tolerance cure for closer sign-off | `loan_id`, `cd_version`, `lender_credit_cure_amount`, `cure_memo` | `proposal_id`, `status`, `closer_approval_required` |

### C. Condition Clearing Tools (`condition.*`)
Automates document verification against underwriter conditions and generates borrower communications.

| Tool Name | Description | Key Inputs | Output |
| :--- | :--- | :--- | :--- |
| `condition_evaluate_large_deposit` | Evaluates Fannie Mae B3-4.2-02 50% income rule against bank, gift, and wire docs | `loan_id`, `condition_id`, `monthly_qualifying_income`, `deposit_amount`, `deposit_date` | `status`, `checks`, `ready_for_processor_review` |
| `condition_draft_loe` | Generates a formatted Letter of Explanation (LOE) for borrower e-signature | `borrower_name`, `property_address`, `subject`, `explanation_body` | `loe_text`, `status` |
| `los_stage_condition_package` | Compiles evidence cover sheet for human processor review | `loan_id`, `condition_id`, `evidence_doc_ids` | `cover_sheet`, `underwriter_submission_allowed` |
| `los_update_condition` | Updates condition notes; refuses `cleared` or `submitted` with `FORBIDDEN_ROLE` | `loan_id`, `condition_id`, `target_status`, `notes` | `status` or policy violation error |

### D. Loan Set-up & Intake Tools (`setup.*`)
Calculates qualifying income, audits bank deposits, and stages URLA 1003 applications.

| Tool Name | Description | Key Inputs | Output |
| :--- | :--- | :--- | :--- |
| `setup_calculate_income` | Deterministic Fannie 1084 income math (salary, hourly, overtime trending) | `income_type`, `amount`, `frequency`, `hours_per_week`, `prior_year_amount`, `ytd_amount`, `ytd_months` | `monthly_amount`, method, rule citation |
| `setup_check_large_deposits` | Scans loan bank statements for deposits $> 50\%$ qualifying income | `loan_id`, `monthly_qualifying_income` | `flagged_deposits`, `count`, threshold |
| `setup_generate_needs_list` | Audits indexed documents and generates missing document checklist | `loan_id` | `missing_documents`, count |
| `los_stage_fields` | Stages proposed URLA draft; rejects Sections 5–8 with `FORBIDDEN_ATTESTATION` | `loan_id`, `section_name`, `fields` | `status` or policy violation error |

### E. Production LOS Queries & Comms (`los.*`, `comms.*`)
Production-parity queries for pipeline inspection and borrower communications.

| Tool Name | Description | Key Inputs | Output |
| :--- | :--- | :--- | :--- |
| `los_get_loan` | Retrieves loan summary, milestone, lock status, and version | `loan_id` | Loan entity record |
| `los_list_documents` | Lists indexed documents, page counts, and metadata | `loan_id` | Document records |
| `los_get_urla` | Retrieves committed vs staged URLA 1003 sections side-by-side | `loan_id` | Staged and committed data |
| `los_list_conditions` | Lists open conditions and linked evidence | `loan_id` | Condition records |
| `los_list_disclosures` | Lists Loan Estimates and Closing Disclosures | `loan_id` | Disclosures with fee items |
| `comms_send_borrower_request` | Sends documentation request with due date | `loan_id`, `request_type`, `message`, `due_date` | `comm_id`, status |
| `comms_get_thread` | Retrieves borrower communications log | `loan_id` | Message thread |

---

## 5. Running the MCP Server

### Option A: SSE Transport (Default)
Starts the FastMCP server over Server-Sent Events (SSE):

```bash
python run_server.py
```
* The SSE endpoint will be available at: `http://localhost:8000/sse`

### Option B: Custom Host/Port or Stdio
You can customize transport parameters directly:

```bash
# Run over stdio (e.g. for Claude Desktop / CLI clients)
python src/mcp_server/server.py --transport stdio

# Run over SSE on custom port
python src/mcp_server/server.py --transport sse --port 8080
```

---

## 6. Testing & Verification

Run the test suite with `pytest`:

```bash
pytest tests/ -v
```

Expected output:
```text
tests/test_calendar_oracle.py::test_t2_thu_receipt_earliest_consummation PASSED [  3%]
tests/test_calendar_oracle.py::test_t3_fri_receipt_earliest_consummation PASSED [  7%]
tests/test_calendar_oracle.py::test_t4_federal_holiday_exclusion PASSED         [ 11%]
tests/test_calendar_oracle.py::test_general_vs_specific_saturday PASSED         [ 14%]
tests/test_condition_engine.py::test_c1_deposit_below_50_pct_threshold PASSED  [ 18%]
tests/test_condition_engine.py::test_c2_deposit_above_threshold_all_match PASSED [ 22%]
tests/test_condition_engine.py::test_c3_donor_name_mismatch PASSED              [ 25%]
tests/test_income_engine.py::test_s3_hourly_income_calculation PASSED           [ 29%]
tests/test_income_engine.py::test_base_salary_frequencies PASSED                [ 33%]
tests/test_income_engine.py::test_s5_urla_declarations_lockout PASSED           [ 37%]
tests/test_income_engine.py::test_needs_list_generation PASSED                  [ 40%]
tests/test_mcp_tools.py::TestTRIDTools::test_trid_audit_disclosure_deck_example PASSED [ 44%]
tests/test_mcp_tools.py::TestTRIDTools::test_trid_check_timing_tool PASSED      [ 48%]
tests/test_mcp_tools.py::TestTRIDTools::test_stage_cd_proposal_tool PASSED     [ 51%]
tests/test_condition_engine.py::TestConditionTools::test_condition_evaluate_large_deposit_tool PASSED [ 55%]
tests/test_condition_engine.py::TestConditionTools::test_tw5_policy_enforcement_cannot_clear_condition PASSED [ 59%]
tests/test_setup_engine.py::TestSetupTools::test_setup_calculate_income_hourly PASSED [ 62%]
tests/test_setup_engine.py::TestSetupTools::test_setup_check_large_deposits PASSED [ 66%]
tests/test_setup_engine.py::TestSetupTools::test_tw6_policy_enforcement_cannot_stage_declarations PASSED [ 70%]
tests/test_mcp_tools.py::TestLOSTraceCommsTools::test_los_queries PASSED       [ 74%]
tests/test_mcp_tools.py::TestLOSTraceCommsTools::test_shared_trace_and_escalate PASSED [ 77%]
tests/test_mcp_tools.py::TestLOSTraceCommsTools::test_comms_tools PASSED        [ 81%]
tests/test_trid_engine.py::test_t1_deck_worked_example_cure_112 PASSED          [ 85%]
tests/test_trid_engine.py::test_t6_shopped_off_spl_no_limit PASSED              [ 88%]
tests/test_trid_engine.py::test_t7_same_fee_chosen_from_spl PASSED              [ 92%]
tests/test_trid_engine.py::test_t9_lender_credit_shortfall PASSED               [ 96%]
tests/test_trid_engine.py::test_apr_drift_trigger PASSED                        [100%]
============================= 27 passed in 3.07s ==============================
```

---

## 7. Connecting to Agent Clients

### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mortgage-twin-server": {
      "command": "python",
      "args": [
        "<path-to-repo>/src/mcp_server/server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```
