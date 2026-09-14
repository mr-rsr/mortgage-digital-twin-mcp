import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.config import settings

class MortgageDatabase:
    """
    Unified Mortgage Database Client.
    Supports live Supabase if configured, otherwise falls back to a self-contained
    SQLite database with full relational and audit capabilities.
    """

    def __init__(self):
        self.use_supabase = bool(settings.supabase_url and settings.supabase_key)
        self.supabase = None

        if self.use_supabase:
            try:
                from supabase import create_client
                self.supabase = create_client(settings.supabase_url, settings.supabase_key)
            except Exception as e:
                print(f"Failed to connect to Supabase: {e}. Falling back to SQLite.")
                self.use_supabase = False

        if not self.use_supabase:
            # Initialize SQLite
            self.sqlite_db_path = settings.local_db_path
            self._init_sqlite()

    def _get_connection(self):
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        conn = self._get_connection()
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS loans (
            id TEXT PRIMARY KEY,
            borrower_name TEXT NOT NULL,
            property_address TEXT NOT NULL,
            program TEXT NOT NULL,
            purpose TEXT NOT NULL,
            occupancy TEXT NOT NULL,
            loan_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            milestone TEXT NOT NULL DEFAULT 'application',
            lock_status TEXT NOT NULL DEFAULT 'unlocked',
            locked_at TEXT,
            version INT NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            type TEXT NOT NULL,
            borrower_name TEXT NOT NULL,
            page_count INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'indexed',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS disclosures (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            type TEXT NOT NULL,
            version INT NOT NULL,
            issued_date TEXT NOT NULL,
            received_date TEXT,
            receipt_method TEXT,
            apr REAL NOT NULL,
            loan_product TEXT NOT NULL,
            prepay_penalty INT NOT NULL DEFAULT 0,
            lender_credits REAL NOT NULL DEFAULT 0.0,
            baseline_ref TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fees (
            id TEXT PRIMARY KEY,
            disclosure_id TEXT NOT NULL,
            code TEXT NOT NULL,
            label TEXT NOT NULL,
            section TEXT NOT NULL,
            amount REAL NOT NULL,
            payee TEXT,
            payee_affiliated INT NOT NULL DEFAULT 0,
            borrower_shopped INT NOT NULL DEFAULT 0,
            on_spl INT NOT NULL DEFAULT 0,
            baseline_amount REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS coc_events (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            known_at TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            description TEXT NOT NULL,
            fees_affected TEXT DEFAULT '[]',
            revised_le_id TEXT,
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conditions (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            category TEXT NOT NULL,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            cited_rule TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            owner TEXT NOT NULL DEFAULT 'borrower',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS condition_evidence (
            id TEXT PRIMARY KEY,
            condition_id TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            page_number INT NOT NULL DEFAULT 1,
            description TEXT NOT NULL,
            verified INT NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS urla_data (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            section_name TEXT NOT NULL,
            committed_data TEXT DEFAULT '{}',
            staged_data TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_trace (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            decision_type TEXT NOT NULL,
            decision_payload TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence_refs TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policy_violations (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            rule_violated TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS escalations (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            context TEXT DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'queued_for_review',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS borrower_comms (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            request_type TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'sent',
            due_date TEXT NOT NULL,
            reminder_sent_at TEXT,
            created_at TEXT NOT NULL
        );
        """)
        conn.commit()
        conn.close()

    # -------------------------------------------------------------
    # Loans & Documents
    # -------------------------------------------------------------
    def get_loan(self, loan_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase.table("loans").select("*").eq("id", loan_id).execute()
            return res.data[0] if res.data else None
        else:
            conn = self._get_connection()
            row = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
            conn.close()
            return dict(row) if row else None

    def list_loans(self) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase.table("loans").select("*").execute()
            return res.data or []
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM loans").fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def list_documents(self, loan_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase.table("documents").select("*").eq("loan_id", loan_id).execute()
            return res.data or []
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM documents WHERE loan_id = ?", (loan_id,)).fetchall()
            conn.close()
            results = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("metadata"), str):
                    try:
                        item["metadata"] = json.loads(item["metadata"])
                    except Exception:
                        pass
                results.append(item)
            return results

    # -------------------------------------------------------------
    # Disclosures & Fees
    # -------------------------------------------------------------
    def get_disclosures_for_loan(self, loan_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            disc_res = self.supabase.table("disclosures").select("*").eq("loan_id", loan_id).order("version").execute()
            disclosures = disc_res.data or []
            for d in disclosures:
                fee_res = self.supabase.table("fees").select("*").eq("disclosure_id", d["id"]).execute()
                d["fees"] = fee_res.data or []
            return disclosures
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM disclosures WHERE loan_id = ? ORDER BY version ASC", (loan_id,)).fetchall()
            disclosures = []
            for r in rows:
                d = dict(r)
                fee_rows = conn.execute("SELECT * FROM fees WHERE disclosure_id = ?", (d["id"],)).fetchall()
                d["fees"] = [dict(f) for f in fee_rows]
                disclosures.append(d)
            conn.close()
            return disclosures

    def get_disclosure(self, disclosure_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase.table("disclosures").select("*").eq("id", disclosure_id).execute()
            if not res.data:
                return None
            disc = res.data[0]
            fees = self.supabase.table("fees").select("*").eq("disclosure_id", disclosure_id).execute()
            disc["fees"] = fees.data or []
            return disc
        else:
            conn = self._get_connection()
            row = conn.execute("SELECT * FROM disclosures WHERE id = ?", (disclosure_id,)).fetchone()
            if not row:
                conn.close()
                return None
            disc = dict(row)
            fee_rows = conn.execute("SELECT * FROM fees WHERE disclosure_id = ?", (disclosure_id,)).fetchall()
            disc["fees"] = [dict(f) for f in fee_rows]
            conn.close()
            return disc

    def get_coc_events(self, loan_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase.table("coc_events").select("*").eq("loan_id", loan_id).execute()
            return res.data or []
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM coc_events WHERE loan_id = ?", (loan_id,)).fetchall()
            conn.close()
            results = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("fees_affected"), str):
                    try:
                        item["fees_affected"] = json.loads(item["fees_affected"])
                    except Exception:
                        pass
                results.append(item)
            return results

    # -------------------------------------------------------------
    # Conditions
    # -------------------------------------------------------------
    def list_conditions(self, loan_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            c_res = self.supabase.table("conditions").select("*").eq("loan_id", loan_id).execute()
            conditions = c_res.data or []
            for c in conditions:
                ev_res = self.supabase.table("condition_evidence").select("*").eq("condition_id", c["id"]).execute()
                c["evidence"] = ev_res.data or []
            return conditions
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM conditions WHERE loan_id = ?", (loan_id,)).fetchall()
            conditions = []
            for r in rows:
                c = dict(r)
                ev_rows = conn.execute("SELECT * FROM condition_evidence WHERE condition_id = ?", (c["id"],)).fetchall()
                c["evidence"] = [dict(e) for e in ev_rows]
                conditions.append(c)
            conn.close()
            return conditions

    def update_condition_status(self, condition_id: str, status: str, notes: Optional[str] = None) -> bool:
        if self.use_supabase:
            update_data = {"status": status}
            self.supabase.table("conditions").update(update_data).eq("id", condition_id).execute()
            return True
        else:
            conn = self._get_connection()
            conn.execute("UPDATE conditions SET status = ? WHERE id = ?", (status, condition_id))
            conn.commit()
            conn.close()
            return True

    # -------------------------------------------------------------
    # URLA Sections
    # -------------------------------------------------------------
    def get_urla_data(self, loan_id: str) -> Dict[str, Any]:
        if self.use_supabase:
            res = self.supabase.table("urla_data").select("*").eq("loan_id", loan_id).execute()
            return {row["section_name"]: row for row in (res.data or [])}
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM urla_data WHERE loan_id = ?", (loan_id,)).fetchall()
            conn.close()
            out = {}
            for r in rows:
                d = dict(r)
                for k in ["committed_data", "staged_data"]:
                    if isinstance(d.get(k), str):
                        try:
                            d[k] = json.loads(d[k])
                        except Exception:
                            pass
                out[d["section_name"]] = d
            return out

    def stage_urla_fields(self, loan_id: str, section_name: str, staged_fields: Dict[str, Any]) -> bool:
        if self.use_supabase:
            existing = self.supabase.table("urla_data").select("*").eq("loan_id", loan_id).eq("section_name", section_name).execute()
            if existing.data:
                curr_staged = existing.data[0].get("staged_data") or {}
                curr_staged.update(staged_fields)
                self.supabase.table("urla_data").update({"staged_data": curr_staged}).eq("id", existing.data[0]["id"]).execute()
            else:
                self.supabase.table("urla_data").insert({
                    "id": f"URLA-{uuid.uuid4().hex[:8]}",
                    "loan_id": loan_id,
                    "section_name": section_name,
                    "committed_data": {},
                    "staged_data": staged_fields,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            return True
        else:
            conn = self._get_connection()
            row = conn.execute("SELECT * FROM urla_data WHERE loan_id = ? AND section_name = ?", (loan_id, section_name)).fetchone()
            if row:
                row_dict = dict(row)
                curr_staged = json.loads(row_dict["staged_data"]) if isinstance(row_dict["staged_data"], str) else (row_dict["staged_data"] or {})
                curr_staged.update(staged_fields)
                conn.execute("UPDATE urla_data SET staged_data = ? WHERE id = ?", (json.dumps(curr_staged), row_dict["id"]))
            else:
                conn.execute(
                    "INSERT INTO urla_data (id, loan_id, section_name, committed_data, staged_data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (f"URLA-{uuid.uuid4().hex[:8]}", loan_id, section_name, "{}", json.dumps(staged_fields), datetime.now(timezone.utc).isoformat())
                )
            conn.commit()
            conn.close()
            return True

    # -------------------------------------------------------------
    # Shared Trace, Policy Violations, Escalations
    # -------------------------------------------------------------
    def write_trace(
        self,
        entity_id: str,
        agent_name: str,
        decision_type: str,
        decision_payload: Dict[str, Any],
        confidence: float,
        evidence_refs: Optional[List[str]] = None
    ) -> str:
        trace_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        refs = evidence_refs or []

        if self.use_supabase:
            entry = {
                "id": trace_id,
                "entity_id": entity_id,
                "agent_name": agent_name,
                "decision_type": decision_type,
                "decision_payload": decision_payload,
                "confidence": float(confidence),
                "evidence_refs": refs,
                "created_at": created_at
            }
            res = self.supabase.table("agent_trace").insert(entry).execute()
            return str(res.data[0]["id"]) if res.data else trace_id
        else:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO agent_trace (id, entity_id, agent_name, decision_type, decision_payload, confidence, evidence_refs, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (trace_id, entity_id, agent_name, decision_type, json.dumps(decision_payload), float(confidence), json.dumps(refs), created_at)
            )
            conn.commit()
            conn.close()
            return trace_id

    def query_trace(self, entity_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            res = self.supabase.table("agent_trace").select("*").eq("entity_id", entity_id).order("created_at").execute()
            return res.data or []
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM agent_trace WHERE entity_id = ? ORDER BY created_at ASC", (entity_id,)).fetchall()
            conn.close()
            results = []
            for r in rows:
                item = dict(r)
                for k in ["decision_payload", "evidence_refs"]:
                    if isinstance(item.get(k), str):
                        try:
                            item[k] = json.loads(item[k])
                        except Exception:
                            pass
                results.append(item)
            return results

    def record_policy_violation(self, entity_id: str, agent_name: str, tool_name: str, rule_violated: str, detail: str) -> str:
        violation_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        if self.use_supabase:
            self.supabase.table("policy_violations").insert({
                "id": violation_id,
                "entity_id": entity_id,
                "agent_name": agent_name,
                "tool_name": tool_name,
                "rule_violated": rule_violated,
                "detail": detail,
                "created_at": created_at
            }).execute()
        else:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO policy_violations (id, entity_id, agent_name, tool_name, rule_violated, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (violation_id, entity_id, agent_name, tool_name, rule_violated, detail, created_at)
            )
            conn.commit()
            conn.close()
        return violation_id

    def list_policy_violations(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_supabase:
            q = self.supabase.table("policy_violations").select("*")
            if entity_id:
                q = q.eq("entity_id", entity_id)
            return q.execute().data or []
        else:
            conn = self._get_connection()
            if entity_id:
                rows = conn.execute("SELECT * FROM policy_violations WHERE entity_id = ?", (entity_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM policy_violations").fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def escalate_to_human(self, entity_id: str, agent_name: str, reason: str, context: Dict[str, Any]) -> str:
        esc_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        if self.use_supabase:
            self.supabase.table("escalations").insert({
                "id": esc_id,
                "entity_id": entity_id,
                "agent_name": agent_name,
                "reason": reason,
                "context": context,
                "status": "queued_for_review",
                "created_at": created_at
            }).execute()
        else:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO escalations (id, entity_id, agent_name, reason, context, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (esc_id, entity_id, agent_name, reason, json.dumps(context), "queued_for_review", created_at)
            )
            conn.commit()
            conn.close()

        self.write_trace(
            entity_id=entity_id,
            agent_name=agent_name,
            decision_type="human_escalation_triggered",
            decision_payload={"escalation_id": esc_id, "reason": reason, "context": context},
            confidence=0.0,
            evidence_refs=[]
        )
        return esc_id

    # -------------------------------------------------------------
    # Borrower Communications
    # -------------------------------------------------------------
    def send_borrower_request(self, loan_id: str, request_type: str, message: str, due_date: str) -> str:
        comm_id = f"COMM-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        if self.use_supabase:
            self.supabase.table("borrower_comms").insert({
                "id": comm_id,
                "loan_id": loan_id,
                "request_type": request_type,
                "message": message,
                "status": "sent",
                "due_date": due_date,
                "created_at": created_at
            }).execute()
        else:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO borrower_comms (id, loan_id, request_type, message, status, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (comm_id, loan_id, request_type, message, "sent", due_date, created_at)
            )
            conn.commit()
            conn.close()
        return comm_id

    def list_borrower_comms(self, loan_id: str) -> List[Dict[str, Any]]:
        if self.use_supabase:
            return self.supabase.table("borrower_comms").select("*").eq("loan_id", loan_id).execute().data or []
        else:
            conn = self._get_connection()
            rows = conn.execute("SELECT * FROM borrower_comms WHERE loan_id = ?", (loan_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]

# Singleton instance
db = MortgageDatabase()
