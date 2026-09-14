-- Seed script for Mortgage Digital Twin in Supabase

INSERT INTO loans (id, borrower_name, property_address, program, purpose, occupancy, loan_amount, interest_rate, milestone, lock_status, locked_at, version)
VALUES ('L-20417', 'John Doe', '123 Elm St, Austin, TX 78701', 'conv_30_fixed', 'purchase', 'primary', 450000.00, 6.875, 'conditional_approval', 'locked', '2026-02-18T10:00:00Z', 1)
ON CONFLICT (id) DO NOTHING;

-- Disclosures
INSERT INTO disclosures (id, loan_id, type, version, issued_date, received_date, receipt_method, apr, loan_product, prepay_penalty, lender_credits, baseline_ref)
VALUES 
('LE-2', 'L-20417', 'LE', 2, '2026-02-20', '2026-02-20', 'e_ack', 6.912, 'conv_30_fixed', FALSE, 0.00, NULL),
('CD-1', 'L-20417', 'CD', 1, '2026-03-18', '2026-03-19', 'e_ack', 6.948, 'conv_30_fixed', FALSE, 0.00, 'LE-2')
ON CONFLICT (id) DO NOTHING;

-- Fees for LE-2
INSERT INTO fees (id, disclosure_id, code, label, section, amount, payee_affiliated, borrower_shopped, on_spl, baseline_amount)
VALUES
('LE-2-origination', 'LE-2', 'origination', 'Origination Charge', 'A', 1200.00, FALSE, FALSE, FALSE, 1200.00),
('LE-2-appraisal', 'LE-2', 'appraisal', 'Appraisal Fee', 'B', 550.00, FALSE, FALSE, FALSE, 550.00),
('LE-2-transfer_taxes', 'LE-2', 'transfer_taxes', 'Transfer Taxes', 'E', 2100.00, FALSE, FALSE, FALSE, 2100.00),
('LE-2-title_lenders_policy', 'LE-2', 'title_lenders_policy', 'Title - Lender Policy', 'C', 900.00, FALSE, FALSE, TRUE, 900.00),
('LE-2-settlement_fee', 'LE-2', 'settlement_fee', 'Settlement Fee', 'C', 600.00, FALSE, FALSE, TRUE, 600.00),
('LE-2-recording', 'LE-2', 'recording', 'Recording Fees', 'E', 180.00, FALSE, FALSE, FALSE, 180.00),
('LE-2-pest_inspection', 'LE-2', 'pest_inspection', 'Pest Inspection', 'C', 150.00, FALSE, TRUE, FALSE, 150.00)
ON CONFLICT (id) DO NOTHING;

-- Fees for CD-1
INSERT INTO fees (id, disclosure_id, code, label, section, amount, payee_affiliated, borrower_shopped, on_spl, baseline_amount)
VALUES
('CD-1-origination', 'CD-1', 'origination', 'Origination Charge', 'A', 1200.00, FALSE, FALSE, FALSE, 1200.00),
('CD-1-appraisal', 'CD-1', 'appraisal', 'Appraisal Fee', 'B', 650.00, FALSE, FALSE, FALSE, 550.00),
('CD-1-transfer_taxes', 'CD-1', 'transfer_taxes', 'Transfer Taxes', 'E', 2100.00, FALSE, FALSE, FALSE, 2100.00),
('CD-1-title_lenders_policy', 'CD-1', 'title_lenders_policy', 'Title - Lender Policy', 'C', 1020.00, FALSE, FALSE, TRUE, 900.00),
('CD-1-settlement_fee', 'CD-1', 'settlement_fee', 'Settlement Fee', 'C', 640.00, FALSE, FALSE, TRUE, 600.00),
('CD-1-recording', 'CD-1', 'recording', 'Recording Fees', 'E', 200.00, FALSE, FALSE, FALSE, 180.00),
('CD-1-pest_inspection', 'CD-1', 'pest_inspection', 'Pest Inspection', 'C', 175.00, FALSE, TRUE, FALSE, 150.00)
ON CONFLICT (id) DO NOTHING;

-- Conditions
INSERT INTO conditions (id, loan_id, category, code, title, description, cited_rule, status, owner)
VALUES
('COND-PTD-07', 'L-20417', 'PTD', 'PTD-07', 'Large Deposit Verification', 'Source $8,500 deposit on checking account ending 4412 dated 02/24/2026', 'Fannie Mae Selling Guide B3-4.2-02', 'open', 'borrower'),
('COND-PTD-02', 'L-20417', 'PTD', 'PTD-02', 'Recent Paystub Verification', 'Provide most recent 30-day paystub reflecting year-to-date earnings', 'Fannie Mae Selling Guide B3-3.1-01', 'open', 'borrower')
ON CONFLICT (id) DO NOTHING;
