import pytest
from src.engines.income_engine import IncomeEngine

def test_s3_hourly_income_calculation():
    """S-3: Hourly borrower ($32.50/hr, 40 hrs/wk) -> $5,633.33/mo."""
    res = IncomeEngine.calculate_hourly_income(hourly_rate=32.50, hours_per_week=40.0)
    assert res["monthly_amount"] == 5633.33

def test_base_salary_frequencies():
    """Fannie 1084 base salary frequencies."""
    # $60,000 annual
    res_ann = IncomeEngine.calculate_base_salary(60000.0, "annual")
    assert res_ann["monthly_amount"] == 5000.00

    # $2,307.69 bi-weekly -> 2307.69 * 26 / 12 = 5000.00
    res_bw = IncomeEngine.calculate_base_salary(2307.69, "bi_weekly")
    assert round(res_bw["monthly_amount"], 0) == 5000.00

def test_s5_urla_declarations_lockout():
    """S-5: AI agent attempting to stage/write URLA Section 5 Declarations is strictly blocked."""
    with pytest.raises(PermissionError) as exc_info:
        IncomeEngine.validate_urla_field_staging("section_5_declarations", "declared_bankruptcy")
    assert "FORBIDDEN_ATTESTATION" in str(exc_info.value)

def test_needs_list_generation():
    """Missing document needs list generation for conv_30_fixed."""
    indexed = ["paystub", "w2"] # Missing bank_statement and purchase_contract
    missing = IncomeEngine.generate_needs_list("conv_30_fixed", indexed)
    missing_types = [m["type"] for m in missing]
    assert "bank_statement" in missing_types
    assert "purchase_contract" in missing_types
    assert "paystub" not in missing_types
