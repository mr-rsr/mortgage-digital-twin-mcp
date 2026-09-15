from datetime import date, datetime, timedelta
from typing import List, Set, Union

class CalendarOracle:
    """
    Independent Calendar Oracle implementing TRID dual-calendar business day rules.
    - General Business Day: Days the lender's offices are open (Mon-Fri, excluding federal holidays).
    - Specific Business Day: All calendar days except Sundays and 11 Federal Legal Public Holidays.
    """

    # 11 Federal Legal Public Holidays for 2026 and 2027
    FEDERAL_HOLIDAYS: Set[date] = {
        # 2026
        date(2026, 1, 1),   # New Year's Day
        date(2026, 1, 19),  # Martin Luther King Jr. Day (3rd Mon in Jan)
        date(2026, 2, 16),  # Washington's Birthday (3rd Mon in Feb)
        date(2026, 5, 25),  # Memorial Day (last Mon in May)
        date(2026, 6, 19),  # Juneteenth National Independence Day
        date(2026, 7, 4),   # Independence Day
        date(2026, 9, 7),   # Labor Day (1st Mon in Sep)
        date(2026, 10, 12), # Columbus Day (2nd Mon in Oct)
        date(2026, 11, 11), # Veterans Day
        date(2026, 11, 26), # Thanksgiving Day (4th Thu in Nov)
        date(2026, 12, 25), # Christmas Day

        # 2027
        date(2027, 1, 1),   # New Year's Day
        date(2027, 1, 18),  # Martin Luther King Jr. Day
        date(2027, 2, 15),  # Washington's Birthday
        date(2027, 5, 31),  # Memorial Day
        date(2027, 6, 19),  # Juneteenth
        date(2027, 7, 5),   # Independence Day (observed)
        date(2027, 9, 6),   # Labor Day
        date(2027, 10, 11), # Columbus Day
        date(2027, 11, 11), # Veterans Day
        date(2027, 11, 25), # Thanksgiving Day
        date(2027, 12, 25), # Christmas Day
    }

    @classmethod
    def _parse_date(cls, d: Union[date, str]) -> date:
        if isinstance(d, str):
            return datetime.strptime(d[:10], "%Y-%m-%d").date()
        return d

    @classmethod
    def is_business_day(cls, d: Union[date, str], calendar_type: str = "specific") -> bool:
        """
        Check if a given date is a business day under TRID definitions.
        - 'general': Monday through Friday, excluding federal holidays.
        - 'specific': Monday through Saturday (Sunday excluded), excluding federal holidays.
        """
        target = cls._parse_date(d)

        # Federal holidays are never business days in either definition
        if target in cls.FEDERAL_HOLIDAYS:
            return False

        weekday = target.weekday() # 0 = Monday, 6 = Sunday

        if calendar_type == "general":
            return weekday < 5 # Mon-Fri
        elif calendar_type == "specific":
            return weekday != 6 # Mon-Sat (Sunday excluded)
        else:
            raise ValueError(f"Unknown calendar_type: {calendar_type}. Use 'general' or 'specific'.")

    @classmethod
    def add_business_days(cls, start: Union[date, str], num_days: int, calendar_type: str = "specific") -> date:
        """
        Add N business days starting from the day AFTER start_date.
        """
        curr = cls._parse_date(start)
        added = 0
        while added < num_days:
            curr += timedelta(days=1)
            if cls.is_business_day(curr, calendar_type=calendar_type):
                added += 1
        return curr

    @classmethod
    def calculate_earliest_consummation(cls, cd_received_date: Union[date, str]) -> date:
        """
        Calculates the earliest permissible consummation date under the 3-day CD rule.
        Rule (12 CFR 1026.19(f)(1)(ii)): Borrower must receive the CD at least
        3 specific business days prior to consummation.
        The day of receipt does not count.
        Counting starts on the next calendar day.
        Day 1, Day 2, Day 3 must be specific business days.
        Consummation can occur on or after the day Day 3 is reached (Day 3 itself is the 3rd business day prior).
        """
        # 3 business days after receipt
        return cls.add_business_days(cd_received_date, 3, calendar_type="specific")

    @classmethod
    def check_le_waiting_period(cls, le_received_date: Union[date, str], consummation_date: Union[date, str]) -> bool:
        """
        LE 7-day rule: Consummation cannot occur earlier than 7 specific business days
        after delivery or mailing of the initial Loan Estimate.
        """
        rec = cls._parse_date(le_received_date)
        cons = cls._parse_date(consummation_date)
        earliest = cls.add_business_days(rec, 7, calendar_type="specific")
        return cons >= earliest
