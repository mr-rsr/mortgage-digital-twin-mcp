import pytest
from src.db.seed_data import seed_database
from src.db.client import db
from src.mcp_server.tools import trace, trid, conditions, setup, los, comms

@pytest.fixture(autouse=True)
def run_seed():
    """Ensure database has fresh synthetic seed data before each test."""
    seed_database()

class TestTRIDTools:
    def test_trid_audit_disclosure_deck_example(self):
        """Verify trid_audit_disclosure returns exact $112.00 total cure on L-20417."""
        res = trid.audit_disclosure(
            loan_id="L-20417",
            cd_disclosure_id="CD-1",
            target_consummation="2026-03-24"
        )
        assert "error" not in res
        tol = res["tolerance"]
        assert tol["zero_bucket"]["cure"] == 100.00
        assert tol["ten_bucket"]["cure"] == 12.00
        assert tol["total_cure"] == 112.00
        assert res["timing"]["wait_met"] is True
        assert res["route"] == "cure_and_send_for_closer_approval"

    def test_trid_check_timing_tool(self):
        """Verify trid_check_timing validates 3-day CD rule."""
        res = trid.check_timing("2026-03-19", "2026-03-24")
        assert res["wait_met"] is True
        assert res["earliest_permissible_consummation"] == "2026-03-23"

    def test_stage_cd_proposal_tool(self):
        """Verify staging CD proposal enforces closer approval gate."""
        res = trid.stage_cd_proposal(
            loan_id="L-20417",
            cd_version=2,
            lender_credit_cure_amount=112.00,
            cure_memo="Tolerance cure: $100 appraisal zero-bucket increase + $12 ten-percent aggregate exceedance."
        )
        assert res["status"] == "staged_for_closer_approval"
        assert res["closer_approval_required"] is True
        assert res["direct_send_to_borrower_allowed"] is False

class TestConditionTools:
    def test_condition_evaluate_large_deposit_tool(self):
        """Verify large deposit evaluation on L-20417."""
        res = conditions.evaluate_large_deposit(
            loan_id="L-20417",
            condition_id="COND-PTD-07",
            monthly_qualifying_income=6000.00,
            deposit_amount=8500.00,
            deposit_date="2026-02-24"
        )
        assert res["status"] == "evidence_complete"
        assert res["ready_for_processor_review"] is True

    def test_tw5_policy_enforcement_cannot_clear_condition(self):
        """TW-5: Agent attempting to clear a condition directly is refused with FORBIDDEN_ROLE."""
        res = conditions.update_condition(
            loan_id="L-20417",
            condition_id="COND-PTD-07",
            target_status="cleared",
            notes="Agent cleared condition automatically."
        )
        assert res["isError"] is True
        assert res["code"] == "FORBIDDEN_ROLE"

        # Verify policy violation was registered in database
        violations = db.list_policy_violations("L-20417")
        assert len(violations) >= 1
        assert violations[-1]["rule_violated"] == "FORBIDDEN_ROLE"

class TestSetupTools:
    def test_setup_calculate_income_hourly(self):
        """Verify setup_calculate_income produces deterministic income math."""
        res = setup.calculate_income(
            income_type="hourly",
            amount=35.00,
            hours_per_week=40.0
        )
        # 35 * 40 * 52 / 12 = 6,066.67
        assert res["monthly_amount"] == 6066.67

    def test_setup_check_large_deposits(self):
        """Verify scan of loan bank statement transactions."""
        res = setup.check_large_deposits(loan_id="L-20417", monthly_qualifying_income=6000.00)
        assert res["count"] == 1
        assert res["flagged_deposits"][0]["amount"] == 8500.00

    def test_tw6_policy_enforcement_cannot_stage_declarations(self):
        """TW-6: Agent attempting to stage URLA Section 5 Declarations is refused with FORBIDDEN_ATTESTATION."""
        res = setup.stage_fields(
            loan_id="L-20417",
            section_name="section_5_declarations",
            fields={"declared_bankruptcy": False}
        )
        assert res["isError"] is True
        assert res["code"] == "FORBIDDEN_ATTESTATION"

        # Verify violation recorded
        violations = db.list_policy_violations("L-20417")
        assert any(v["rule_violated"] == "FORBIDDEN_ATTESTATION" for v in violations)

class TestLOSTraceCommsTools:
    def test_los_queries(self):
        """Verify LOS query tools."""
        loan = los.get_loan("L-20417")
        assert loan["borrower_name"] == "John Doe"

        docs = los.list_documents("L-20417")
        assert docs["count"] >= 4

        conds = los.list_conditions("L-20417")
        assert conds["count"] >= 2

    def test_shared_trace_and_escalate(self):
        """Verify shared append-only audit trace and human escalation queue."""
        res_trace = trace.write_decision(
            entity_id="L-20417",
            agent_name="TestAgent",
            decision_type="test_decision",
            decision_payload={"result": "valid"},
            confidence=0.99
        )
        assert res_trace["status"] == "success"

        q_res = trace.query("L-20417")
        assert q_res["count"] >= 1

        esc_res = trace.escalate_to_human(
            entity_id="L-20417",
            agent_name="TestAgent",
            reason="Ambiguous borrower document signature",
            context={"doc_id": "DOC-GIFT-01"}
        )
        assert esc_res["status"] == "queued_for_review"

    def test_comms_tools(self):
        """Verify borrower request sending and thread inspection."""
        send_res = comms.send_borrower_request(
            loan_id="L-20417",
            request_type="needs_list",
            message="Please provide your fully executed purchase agreement.",
            due_date="2026-03-25"
        )
        assert send_res["status"] == "sent"

        thread = comms.get_thread("L-20417")
        assert thread["count"] >= 1
