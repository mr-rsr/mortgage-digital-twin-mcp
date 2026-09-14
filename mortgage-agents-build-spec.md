# Mortgage Loan-File Agents: Consolidated Research and Build Spec

Version 1.0 · Sept 30, 2026
Inputs: the "Agentic AI in Mortgage" deck (initial research) plus a market, regulatory and integration scan.
Status tags used below: **[V]** verified against a primary or named source, **[S]** secondary or vendor source, **[D]** design decision (ours, change if you disagree), **[C]** confirm with counsel or the lender before building.

---

## 1. Consolidated findings

### 1.1 The three problems, restated

| # | Problem | Why it costs money | Where the agent works |
|---|---|---|---|
| 1 | Loan set-up: intake, indexing, URLA keying, income and asset math, needs list | Processor hours before underwriting can start. Personnel is 67% of origination cost **[V]** (Freddie Mac 2024 study; $11,600 per loan Q3 2023, about $11,800 in the 2025 update). | Read documents, populate the file, calculate, ask for what is missing |
| 2 | Conditions after conditional approval | Each open condition holds the file in suspense; re-submission rounds add days | Match evidence to each condition, check against the cited guide section, draft the response |
| 3 | Closing Disclosure vs Loan Estimate review | Tolerance cures, missed re-disclosure, delayed closing. One secondary source cites ICE data at 35% of loans needing a cure, $1,225 average **[S]** | Compute tolerance and timing, route the exceptions |

### 1.2 Market

- The category is live. **Areal AI** (Copilot processor and closer agents, CD Balancer, Encompass/MeridianLink/Byte integrations, patent pending, named customers) **[S]**. **TRUE** (loan set-up, underwriting, processing and closing) **[S]**. **Loancrate** (condition clearing) **[S]**. **Sei AI** (tolerance and large-deposit agents that compute and hand judgment to a human) **[S]**. **Infrrd** (CD reconciliation; tolerance logic was "planned" as of 2025) **[S]**. **Multimodal, Uptiq, Addy AI** (document AI, auto-clearing, pre-underwriting) **[S]**. **TD Bank** launched agentic pre-adjudication in May 2026 **[V]**.
- Vendors agree on the shape: narrow agents, exceptions-only routing, a human owning credit and compliance judgment, LOS write-back.
- Areal names CD balancing its most common first workflow: clearest outcome, lowest integration friction **[S]**.
- All performance claims (minutes saved, auto-clear rates) are marketing. Nothing here is a benchmark until we measure it.

### 1.3 Regulation that shapes the product

- **Fannie Mae LL-2026-04** (issued Apr 8, effective Aug 6, 2026) requires a documented, maintained AI/ML governance program for sellers and servicers using AI in origination or servicing. Policies must be transparent, reviewed at least annually, and vendor and subcontractor AI must be governed "no less protective" than the lender's own. On request the lender must disclose the types of AI used, its purpose and manner, and safeguards **[V]**.
- **Freddie Mac Guide Bulletin 2025-16** amended Seller/Servicer Guide sections 1302.2 and 1302.8 with a more prescriptive AI/ML framework, effective Mar 3, 2026 **[V]**.
- **Consequence for us:** we are the "vendor AI" in a lender's governance program. We must ship the artifacts they will be asked for (model inventory, purpose statement, safeguards, audit trail, change log). This is a feature, not paperwork. **[D]**
- **TRID (12 CFR 1026.19(e), (f))**: rule details are in section 4.3. Encode from the regulation text and have counsel sign off **[C]**.

### 1.4 Guide facts the agents depend on

- **Large deposit** (Fannie Selling Guide B3-4.2-02): a single deposit above 50% of total monthly qualifying income, evaluated when bank statements (typically two months) are used. Sources evident on the statement (payroll direct deposit, SSA, tax refund, transfer between own accounts) need no extra documentation. DU's validation service can flag deposits needing documentation, and complying with DU's messages satisfies the requirement **[V]**.
- **Implication:** the rule engine must read DU messages first, apply the 50% test itself only when DU validation isn't in play, and encode purchase vs refinance treatment from the current guide text, not from memory **[C]**. Sources conflict on refinance handling in secondary content, which is exactly why this is versioned data and not hard-coded.
- The guide text changes. Rules are effective-dated records, never string literals in code. **[D]**

### 1.5 Integration facts (Encompass first)

- Encompass Developer Connect exposes REST APIs for loans, eFolder documents and attachments (V3 recommended, V1 still in use), conditions, milestones, disclosure tracking, custom fields, locks, and event webhooks (loan created/updated/locked, field-change events) **[V]**.
- Loan V3 APIs can run calculations and business rules configured on virtual fields; log APIs (documents, conditions, milestones, disclosure tracking) are covered **[V]**.
- Instance credentials are required for real calls; the reference is browsable without them **[V]**. Expect a sandbox and partner onboarding lead time. **[C]**
- MeridianLink and Byte are the next connectors. Their API depth wasn't checked. Treat as unknown until an integration spike. **[C]**

---

## 2. Product definition

**One platform, three agents, one loan-file state.**

| Agent | Trigger | Output | Human gate |
|---|---|---|---|
| A1 Set-up | Borrower upload complete, or LOS "application" milestone | Indexed stack, populated URLA draft, income worksheet, needs list | Loan officer reviews URLA; borrower answers declarations and signs; processor reviews exceptions |
| A2 Conditions | Conditional approval received and assigned | Condition package: cover sheet per condition, matched evidence, drafted LOEs, open-items list | Processor reviews and submits; underwriter clears |
| A3 Disclosure review | CD draft created in LOS | Tolerance and timing findings, cure calculation, draft CD v2 credit, cure memo | Closer approves before anything reaches the borrower; compliance can open every check |

**Build order [D]:** platform, then A3, then A2, then A1. A3 has the cleanest rules and the sharpest ROI. A2 reuses the same evidence-and-rule engine. A1 is the most commoditized and carries the highest extraction-accuracy burden.

**What the agents never do.** Make or communicate a credit decision. Clear a condition. Send a disclosure to a borrower. Answer or infer borrower attestations (declarations, demographics, military service, acknowledgments). Write to a locked or investor-delivered loan.

---

## 3. Architecture

### 3.1 Principle: models read and draft, code decides

| Task type | Done by | Why |
|---|---|---|
| Classify pages, extract fields, read unstructured fee sheets and COC notes, draft LOEs and memos, map a condition to a rule | Model, with structured output and validation | Unstructured input |
| Income math, large-deposit thresholds, tolerance buckets, cure amounts, APR difference, business-day counting | Deterministic code with unit tests | Must be exact and reproducible |
| Whether something is a valid changed circumstance, whether a condition is satisfied, whether a deposit is acceptable | Model proposes with citation; human decides | Judgment |

### 3.2 Components

```
LOS (Encompass / MeridianLink / Byte)
   ^  webhooks in, REST out
   |
[Connector layer]  -- normalizes LOS objects to our schema
   |
[Loan-file state store]  (documents, fields, conditions, disclosures, events)
   |
[Orchestrator]  -- per-loan workflow engine, retries, timers (48h reminder), idempotency
   |
   +-- [Document service]   classify, split, dedupe, OCR, extract
   +-- [Rules service]      versioned, effective-dated guide and TRID rules
   +-- [Calc service]       income, assets, tolerance, APR, dates (pure code)
   +-- [Agent runtime]      LLM calls with tool access, schema-validated outputs
   +-- [Review UI]          processor, closer, compliance queues with evidence viewer
   +-- [Audit + governance] immutable log, model inventory, exports
```

### 3.3 Core data model (minimum)

```
loan            (id, los_id, program, purpose, occupancy, milestone, locked_at, ...)
borrower        (id, loan_id, role, name, ssn_last4_hash, ...)
document        (id, loan_id, los_doc_id, type, borrower_id, pages[], source, received_at, status)
extracted_field (id, doc_id, page, bbox, name, value, confidence, extractor_version, verified_by)
income_line     (id, loan_id, borrower_id, source_doc_ids[], method, inputs{}, monthly_amount, rule_id)
asset_line      (id, loan_id, account_id, balance, statement_period, source_doc_id)
deposit_flag    (id, asset_line_id, date, amount, threshold, source_identified, status)
condition       (id, loan_id, los_cond_id, category[PTD|PTF], text, cited_rule, status, owner)
evidence_link   (id, condition_id, doc_id, page, rationale, rule_id, confidence)
disclosure      (id, loan_id, type[LE|CD], version, issued_at, received_at, method, coc_id)
fee             (id, disclosure_id, code, label, section, amount, payee, payee_affiliated, borrower_shopped, on_spl)
coc_event       (id, loan_id, occurred_at, known_at, reason_code, fees_affected[], revised_le_id)
finding         (id, loan_id, agent, check_id, result[pass|fail|review], detail{}, rule_id, evidence[])
rule            (id, source, section, effective_from, effective_to, logic_ref, text_hash)
review_action   (id, finding_or_package_id, user, action, timestamp, note)
audit_event     (id, actor[agent|user|system], type, payload_hash, model_version, rule_versions[], ts)
```

### 3.4 LOS write-back contract (Encompass mapping) **[D]**

| We produce | Written to | Mode |
|---|---|---|
| Classified, renamed, split documents | eFolder documents and attachments (V3) | Direct |
| Populated URLA fields | Loan fields via V3 Update Loan | Staged to a draft tab or custom fields first; committed on loan officer approval |
| Income worksheet, condition cover sheets, cure memo | eFolder attachments | Direct |
| Condition responses | Conditions log (attach evidence, set status to "Submitted" only by the processor's action) | Human action required |
| Findings and agent status | Custom fields plus a task in the workflow task pipeline | Direct |
| Corrected CD or lender-credit line | Staged proposal; the closer applies it in the LOS | Human action required |

Rules: idempotent writes keyed by loan id, object id and content hash. Never overwrite a field a human has edited; raise a conflict instead. Respect locks.

### 3.5 Model and extraction controls **[D]**

- Every model output is JSON validated against a schema; invalid output is retried once, then routed to a human.
- Critical fields (income amounts, balances, dates, names, loan amount, SSN, account numbers) use two independent extractions. Disagreement means human review.
- Confidence thresholds per field type, configurable per lender. Below threshold means review queue, never silent acceptance.
- Prompts, model versions and rule versions are pinned per run and stored in the audit event.
- Evaluation harness: a golden set of labeled loan files per program, rerun on every prompt, model or rule change. Ship gate is a regression-free run.

---

## 4. Agent specs

### 4.1 A3: Closing Disclosure and TRID review (build first)

**Trigger.** CD draft created, or any fee change after CD v1, or LE revision.

**Workflow (state machine).**
`INTAKE -> NORMALIZE_FEES -> BUCKET -> TOLERANCE -> COC_CHECK -> TIMING -> APR -> ROUTE -> AWAIT_CLOSER -> DONE`
Any step can move to `NEEDS_HUMAN` with a reason code.

**Inputs.** All LE versions, CD versions, title/settlement fee sheet, COC log, lock history, service provider list (SPL), application date, consummation date, delivery and receipt records.

**Fee bucketing rules (encode as data, effective-dated) [C].**

| Bucket | Applies to | Compare against |
|---|---|---|
| Zero tolerance | Lender, broker and affiliate fees; transfer taxes; fees for services the borrower was not permitted to shop for; reduction in lender credits below the LE estimate (CFPB FAQ, comment 19(e)(3)(i)-5) **[V]** | Baseline amount, per fee |
| 10% aggregate | Recording fees; third-party services the borrower could shop for but selected from the lender's written list | Sum of baseline amounts x 1.10, per bucket |
| No limit (good faith) | Prepaids, escrow deposits, insurance and tax items, third-party services the borrower shopped for and chose off the list | Good-faith check only |

Fee mapping is a lookup table plus attributes (`payee_affiliated`, `borrower_shopped`, `on_spl`). The model may propose attribute values from the fee sheet; a human confirms low-confidence ones.

**Baseline.** Amount on the last LE that was valid for that fee. A revised LE resets the baseline only if a valid changed circumstance (or borrower request or expiry) supports it and it met the redisclosure window.

**Tolerance algorithm (pure code).**

```
for fee in zero_bucket:
    cure += max(0, cd_amount - baseline)          # per fee
for bucket10 in ten_percent_fees:
    limit = round(sum(baseline) * 1.10, 2)
    cure += max(0, sum(cd_amount) - limit)        # aggregate
lender_credit_shortfall = max(0, le_credit - cd_credit)
cure += lender_credit_shortfall
```

Worked check from the deck: appraisal 550 -> 650 (zero) gives 100. 10% bucket baseline 1,680, limit 1,848, CD 1,860 gives 12. Total 112. This is unit test T-1.

**Changed-circumstance check.** Valid reason categories to encode **[C]**: extraordinary event; information the lender relied on that was inaccurate or changed; new information the lender did not rely on; borrower-requested change; rate-lock dependent charges; LE expiration; delayed settlement on new construction. For each COC event the code checks: reason code present, occurred before the change, revised LE issued within 3 business days of the lender learning of it, fees on the revised LE match the fees the reason can justify. The model reads the free-text COC note and proposes a reason code and a justification sentence. Result is `pass`, `fail` or `review`. Only `pass` resets a baseline. Thin cases are always `review`.

**Timing checks (pure code) [C].**

| Check | Rule | Business-day definition |
|---|---|---|
| LE delivery | Within 3 business days after the six application items are received | General: days the lender's offices are open for substantially all business functions |
| LE waiting period | Borrower receives LE at least 7 business days before consummation | Specific: all calendar days except Sundays and federal holidays |
| Revised LE cutoff | Borrower receives revised LE no later than 4 business days before consummation | Specific |
| Revised LE after COC | Issued within 3 business days of learning of the change | General |
| CD waiting period | Borrower receives CD at least 3 business days before consummation | Specific |
| New CD wait triggers | APR becomes inaccurate (over 1/8 point regular, 1/4 point irregular), loan product changes, prepayment penalty added | n/a |
| Cure window | Refund plus corrected CD within 60 days after consummation | Calendar days |

Receipt: use the borrower's e-acknowledgment or delivery record. If none, apply the mailing/electronic presumption of receipt three business days after delivery, per the regulation **[C]**. The clock runs from receipt, not send.

**APR test.** Compare the APR on the CD the borrower already received to the APR recalculated on the corrected CD (including any cure credit). Fail if the difference exceeds 1/8 point (1/4 for irregular). Flag product change and prepayment penalty by field comparison. The APR itself is computed by the LOS or a certified calculator; the agent never computes APR with a model **[D]**.

**Routing outputs.**
- No issues: `clear_to_send` recommendation to the closer.
- Cure only: draft lender-credit line for CD v2 (Section J), cure memo, variance table. No new waiting period unless APR, product or penalty triggers apply.
- Re-disclosure trigger: compute earliest permissible consummation date, alert closer and loan officer.
- Review items: itemized, with the rule and evidence.

**Output schema (excerpt).**

```json
{
  "loan_id": "20417",
  "cd_version": 1,
  "tolerance": {
    "zero": [{"fee":"Appraisal","baseline":550,"cd":650,"cure":100,"coc":"none"}],
    "ten_pct": {"baseline_sum":1680,"limit":1848,"cd_sum":1860,"cure":12},
    "lender_credit_shortfall": 0,
    "total_cure": 112
  },
  "timing": {"cd_received":"2026-03-19","consummation":"2026-03-24",
             "earliest_consummation":"2026-03-23","wait_met":true},
  "apr": {"cd_v1":6.948,"cd_v2_recalc":null,"diff":null,"trigger":null},
  "route": "cure_and_send_for_closer_approval",
  "review_items": [],
  "rule_versions": ["TRID-1026.19-2026-01"],
  "evidence": [{"doc":"title_fee_sheet","page":1}]
}
```

**Acceptance tests.**

| ID | Given | Then |
|---|---|---|
| T-1 | Deck example fees | total_cure = 112; 03/05 appraisal increase with no COC keeps baseline at 550 |
| T-2 | CD received Thu 03/19/2026 | earliest consummation Mon 03/23/2026 (Fri, Sat, Mon counted; Sunday excluded); Tue 03/24 passes |
| T-3 | Consummation 03/23 but CD received Fri 03/20 | Fail: earliest is Tue 03/24 |
| T-4 | Federal holiday inside the window | Holiday excluded from specific-definition count |
| T-5 | APR moves 0.13 point between CD v1 and recalculated CD v2 | New 3-day wait required; consummation date blocked |
| T-6 | Borrower shopped a fee and chose off the SPL | Fee lands in no-limit bucket |
| T-7 | Same fee, chosen from the lender's SPL | Fee lands in 10% bucket |
| T-8 | COC note is ambiguous | Result `review`, baseline unchanged, never auto-reset |
| T-9 | Lender credit lower on CD than LE | Shortfall counted as cure |
| T-10 | Agent finishes | No CD is sent; closer approval recorded before status changes |

**Metrics.** Cure dollars per loan; breaches caught before delivery vs found post-closing (target zero post-closing); closer minutes per CD; false cure rate (cures the closer overrules); rule-version drift incidents.

### 4.2 A2: Condition clearing

**Trigger.** Conditional approval received and assigned to the agent by the processor.

**Workflow.** `PARSE -> CLASSIFY -> MAP_RULE -> MATCH_EVIDENCE -> VALIDATE -> DRAFT -> REQUEST -> PACKAGE -> AWAIT_PROCESSOR`

| Step | Detail |
|---|---|
| PARSE | Extract each condition: text, category (PTD or PTF), cited guide section, owner |
| CLASSIFY | Documentation/verification, third-party (title, appraisal, insurance, HOA), or judgment. Judgment items go straight to the processor with the underwriter's note; the agent does nothing further |
| MAP_RULE | Resolve the cited section (or infer the likely one, flagged as inferred) in the rules service; load the requirement as structured checks (required documents, recency, completeness, thresholds) |
| MATCH_EVIDENCE | Search the loan-file state for candidate documents and fields; return page-level evidence links |
| VALIDATE | Run the structured checks in code where possible (dates within 30 days, all pages present, balance and name match, deposit above 50% threshold). Model handles content that needs reading |
| DRAFT | Cover sheet per condition (rule, evidence, page refs, status). LOE draft for borrower e-signature where the rule calls for one |
| REQUEST | Send the borrower a specific request for anything missing; 48-hour reminder, then reassign to loan officer |
| PACKAGE | Assemble and upload to the LOS; assign to processor |

**Stop conditions (never force a fit).** Evidence doesn't satisfy the rule; a new document raises a new issue (new inquiry, employment change, new debt); deposit source can't be established; conflicting documents. Each produces a flag with the specific gap and the rule reference.

**Worked example (build as fixture).** Loan 20417, condition PTD-07 "source deposit", $8,500 on the checking account. Agent computes 50% of monthly qualifying income, confirms the deposit exceeds it, checks whether DU flagged it, finds two bank statements, a signed gift letter and a donor transfer receipt, validates donor and amount match, drafts a cover sheet, and hands to the processor. Use a deposit date that fits the loan timeline (for example 02/24, before conditional approval).

**Acceptance tests.**

| ID | Given | Then |
|---|---|---|
| C-1 | Deposit below 50% threshold | No condition action beyond noting the calculation |
| C-2 | Deposit above threshold, gift letter and transfer evidence match | Package marked "evidence complete", still requires processor review |
| C-3 | Gift letter donor name differs from transfer receipt | Flag, no package |
| C-4 | Paystub older than the required recency | Request new paystub from borrower; timer set |
| C-5 | Borrower silent for 48 hours | Reminder sent; item reassigned to loan officer |
| C-6 | New credit inquiry appears in updated report | Flag as new issue; agent stops on that condition |
| C-7 | Third-party condition (insurance binder) | Tracked and chased; status never set to satisfied by the agent |
| C-8 | Any completed package | Cannot reach the underwriter without a processor action recorded |

**Metrics.** Processor minutes per condition; same-day return rate; first-pass acceptance by underwriting; re-condition rate and reasons; false "ready" rate (target zero).

### 4.3 A1: Loan set-up and URLA

**Trigger.** Borrower marks upload complete, or the loan reaches the application milestone.

**Workflow.** `INGEST -> CLASSIFY_SPLIT -> EXTRACT -> RECONCILE -> CALCULATE -> POPULATE -> NEEDS_LIST -> AWAIT_REVIEW`

| Step | Detail |
|---|---|
| CLASSIFY_SPLIT | Page-level classification, bundled PDF splitting, duplicate removal, borrower attribution; write to eFolder |
| EXTRACT | Fields per document type from a maintained schema (paystub: employer, pay period, YTD, rate; W-2: box values; bank statement: account, period, balances, transactions; etc.). Dual extraction for critical fields |
| RECONCILE | Cross-document checks: employer on paystub vs credit report and application; balances vs stated assets; names and addresses; SSN; property address vs contract |
| CALCULATE | Income calculators by income type (see below); asset totals; large-deposit detection using the loan's own qualifying income; liabilities from the tri-merge credit report; occupancy and purpose |
| POPULATE | URLA Sections 1 to 4, 9 and L1 to L4 written to a staged draft |
| NEEDS_LIST | Missing and stale documents, generated from a per-program checklist; sent to the borrower; same-day |
| AWAIT_REVIEW | Loan officer reviews URLA; processor reviews exceptions |

**Hard rules.**
- Sections 5 (declarations), 6, 7 and 8 are borrower-only. The agent may show the loan officer file evidence that conflicts with a likely answer (for example a bankruptcy on the credit report); it never fills the answer. **[D]**
- Never add an income source that has no document.
- If DU or LPA findings are available, defer to them for validation messages.

**Income calculators (pure code, one module per type) [D].** Base salary, hourly (with hours evidence), overtime and bonus (multi-year averaging with trend check), commission, self-employed (schedule-based), rental, Social Security and pension. Each returns `monthly_amount`, `method`, every input with document and page, and `rule_id`. Build against Fannie Mae Form 1084 methodology and the applicable program rules; FHA, VA and USDA get their own rule sets **[C]**. The processor sees the full worksheet, not a total.

**Acceptance tests.**

| ID | Given | Then |
|---|---|---|
| S-1 | Paystub employer differs from credit report | Stop on that item, flag with both values and pages |
| S-2 | Bundled 60-page PDF with 3 duplicates | Split, typed, duplicates removed, all pages accounted for |
| S-3 | Hourly borrower, YTD and prior-year W-2 | Worksheet reproduces a hand-calculated reference within $1 per month |
| S-4 | Undocumented side income mentioned in a note | Not counted; flagged |
| S-5 | Declarations section | Untouched; conflicting evidence shown separately |
| S-6 | Borrower upload incomplete | Agent waits; no partial URLA committed |
| S-7 | Extraction disagreement on a critical field | Human review; no write to LOS |
| S-8 | Locked loan | No write; alert raised |

**Metrics.** Field-level extraction accuracy on critical fields; processor minutes per file; income worksheet variance vs processor reference; needs-list turnaround; suspense items at first underwriting review.

---

## 5. Governance features (ship with v1)

Because Fannie LL-2026-04 and Freddie's sections 1302.2 and 1302.8 push AI governance onto lenders and their vendors, the platform includes:

| Feature | Purpose |
|---|---|
| Model and agent inventory export | Types of AI used, purpose and manner, per agent |
| Safeguards register | Human gates, thresholds, stop conditions, per agent |
| Immutable audit trail with export | Reconstruct any decision: inputs, model version, rule version, output, reviewer |
| Change log | Every prompt, model, rule and threshold change, with reviewer and eval result |
| Evaluation reports | Accuracy and exception rates per release, shareable with the lender's risk team |
| Access and data controls | Role-based access, PII encryption, retention by lender policy, SOC 2 |
| Annual review pack | Supports the lender's at-least-annual policy review |

Confirm with counsel which items map to which sections of the Fannie and Freddie documents before making any compliance claim to customers **[C]**.

---

## 6. Non-functional requirements

| Area | Target [D] |
|---|---|
| Latency | A3 review under 2 minutes; A2 package same business day; A1 first pass within 15 minutes of upload complete |
| Availability | 99.9% during lender business hours |
| Reliability | Idempotent, resumable workflows; no duplicate LOS writes |
| Security | SOC 2 Type II path from day one; tenant isolation; encryption in transit and at rest; no customer data used to train models |
| Observability | Per-loan trace of every step; alerting on exception rate, extraction disagreement rate, LOS write failures |
| Rules maintenance | Rule change to production in under 5 business days with eval pass |

---

## 7. Delivery plan (assumptions, not commitments)

Assume a team of about 6 to 8: 3 backend, 1 to 2 ML/eval, 1 frontend, 1 mortgage domain lead (a former processor or closer), 1 product. **[D]**

| Phase | Weeks | Deliverable | Exit test |
|---|---|---|---|
| 0 | 1 to 6 | Encompass sandbox access, connector, state store, audit log, rules service skeleton, calc service with business-day and tolerance code, eval harness | T-1 to T-4 pass; read and write round trip on test loans |
| 1 | 7 to 12 | A3 in shadow mode on closed loans, then live with closer approval | Finds every historical cure in the sample; false-cure rate under a threshold agreed with the pilot lender |
| 2 | 13 to 20 | A2 for documentation and verification conditions | Same-day return and first-pass acceptance beat the lender's baseline |
| 3 | 21 to 30 | A1 intake, worksheet, needs list; MeridianLink connector spike | S-tests pass; processor minutes per file measured |

**Pilot design.** One lender, one LOS, one program mix, 200 to 500 closed loans replayed for A3 shadow mode. Capture the lender's own baseline first (minutes per condition, cure dollars, re-condition rate, minutes to set up). The deck's minute figures are placeholders until then.

**Data needs from the pilot lender.** Historical loans with LE, CD, fee sheets, COC logs and cure records; conditional approvals with final outcomes; SPL; guideline overlays; LOS sandbox; a named processor, closer and compliance reviewer.

---

## 8. Open items

1. Lender segment: independent mortgage banks, banks or credit unions. Determines LOS priority and overlay complexity.
2. Rules library: build in-house or license. Either way it needs an owner and an update cadence.
3. Document extraction: buy or build. Areal and TRUE already sell it; a lender may prefer one vendor for intake. Decide after a bake-off on your own golden set.
4. MeridianLink and Byte API depth (unverified).
5. Counsel review of TRID encoding, business-day definitions, receipt presumptions, and the AI-governance mapping.
6. Refinance vs purchase treatment of large deposits: encode from the current Selling Guide text; secondary sources conflict.
7. Whether to write to a staged draft or directly to URLA fields in the LOS, per lender preference.

---

## Sources

- Fannie Mae Lender Letter LL-2026-04 (singlefamily.fanniemae.com); Orrick and Cooley summaries; Harris Beach Murtha and NMP coverage of the Aug 6, 2026 effective date and Freddie Mac Bulletin 2025-16
- Fannie Mae Selling Guide B3-4.2-02, Depository Accounts (selling-guide.fanniemae.com)
- CFPB TILA-RESPA Integrated Disclosure FAQs (consumerfinance.gov)
- ICE Mortgage Technology, Encompass Developer Connect docs and release notes (developer.icemortgagetechnology.com)
- Freddie Mac 2024 Cost to Originate Study and 2025 update (sf.freddiemac.com)
- TD Bank agentic AI announcement, May 21, 2026 (stories.td.com)
- Vendor material, unverified claims: Areal AI, TRUE, Loancrate, Sei AI, Infrrd, Multimodal, Uptiq, Addy AI
- ICE fee cure statistics via mortgageworkspace.com (secondary)
