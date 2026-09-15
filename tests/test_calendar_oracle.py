from datetime import date
from src.engines.calendar_oracle import CalendarOracle

def test_t2_thu_receipt_earliest_consummation():
    """T-2: CD received Thu 03/19/2026 -> earliest consummation Mon 03/23/2026."""
    rec = "2026-03-19"
    earliest = CalendarOracle.calculate_earliest_consummation(rec)
    assert earliest == date(2026, 3, 23)

    # Tue 2026-03-24 passes wait period
    target = date(2026, 3, 24)
    assert target >= earliest

def test_t3_fri_receipt_earliest_consummation():
    """T-3: CD received Fri 03/20/2026 -> earliest consummation Tue 03/24/2026."""
    rec = "2026-03-20"
    earliest = CalendarOracle.calculate_earliest_consummation(rec)
    assert earliest == date(2026, 3, 24)

    # Mon 2026-03-23 fails wait period
    target = date(2026, 3, 23)
    assert target < earliest

def test_t4_federal_holiday_exclusion():
    """T-4: Federal Holiday inside the wait window is excluded from specific calendar count."""
    # Memorial Day 2026 is Monday, May 25, 2026
    # CD received on Thursday, May 21, 2026:
    # Fri May 22 (Day 1)
    # Sat May 23 (Day 2)
    # Sun May 24 (Excluded - Sunday)
    # Mon May 25 (Excluded - Memorial Day)
    # Tue May 26 (Day 3) -> Earliest Consummation is Tuesday, May 26
    rec = "2026-05-21"
    earliest = CalendarOracle.calculate_earliest_consummation(rec)
    assert earliest == date(2026, 5, 26)

def test_general_vs_specific_saturday():
    """Saturday is a specific business day, but NOT a general business day."""
    saturday = "2026-03-21"
    assert CalendarOracle.is_business_day(saturday, calendar_type="specific") is True
    assert CalendarOracle.is_business_day(saturday, calendar_type="general") is False
