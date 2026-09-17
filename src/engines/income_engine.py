from typing import Any, Dict, List, Optional

class IncomeEngine:
    """
    Deterministic Income Math & Safe URLA Staging Engine.
    Conforms to Fannie Mae Form 1084 and URLA (Form 1003) regulatory attestation guards.
    """

    FORBIDDEN_URLA_SECTIONS = {
        "section_5", "section_5_declarations", "declarations",
        "section_6", "section_6_demographics", "demographics",
        "section_7", "section_7_military", "military",
        "section_8", "section_8_attestation", "acknowledgments"
    }

    @classmethod
    def calculate_base_salary(cls, amount: float, frequency: str) -> Dict[str, Any]:
        """
        Calculates monthly qualifying income from base salary.
        Frequency: 'weekly', 'bi_weekly', 'semi_monthly', 'monthly', 'annually'
        """
        freq = frequency.lower().replace("-", "_")
        if freq == "weekly":
            monthly = round(amount * 52 / 12, 2)
            method = "amount * 52 / 12"
        elif freq == "bi_weekly":
            monthly = round(amount * 26 / 12, 2)
            method = "amount * 26 / 12"
        elif freq == "semi_monthly":
            monthly = round(amount * 24 / 12, 2)
            method = "amount * 2"
        elif freq == "monthly":
            monthly = round(amount, 2)
            method = "stated monthly base"
        elif freq in ["annually", "annual"]:
            monthly = round(amount / 12, 2)
            method = "annual salary / 12"
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")

        return {
            "income_type": "base_salary",
            "input_amount": amount,
            "frequency": frequency,
            "monthly_amount": monthly,
            "calculation_method": method,
            "rule_citation": "Fannie Mae Selling Guide B3-3.1-01"
        }

    @classmethod
    def calculate_hourly_income(cls, hourly_rate: float, hours_per_week: float = 40.0) -> Dict[str, Any]:
        """
        Calculates monthly qualifying income for hourly employee.
        Formula: hourly_rate * hours_per_week * 52 / 12.
        """
        monthly = round((hourly_rate * hours_per_week * 52) / 12, 2)
        return {
            "income_type": "hourly",
            "hourly_rate": hourly_rate,
            "hours_per_week": hours_per_week,
            "monthly_amount": monthly,
            "calculation_method": f"${hourly_rate:.2f} * {hours_per_week} hrs/wk * 52 wks / 12 mos",
            "rule_citation": "Fannie Mae Selling Guide B3-3.1-02"
        }

    @classmethod
    def calculate_overtime_or_bonus(
        cls,
        prior_year_amount: float,
        current_year_ytd_amount: float,
        ytd_months: float
    ) -> Dict[str, Any]:
        """
        Calculates 2-year average for variable income (overtime/bonus) per Fannie Mae Form 1084.
        Checks for declining trend.
        """
        total_months = 12.0 + ytd_months
        total_earnings = prior_year_amount + current_year_ytd_amount
        two_year_monthly_avg = round(total_earnings / total_months, 2)

        # Annualized current rate
        current_monthly_rate = round(current_year_ytd_amount / ytd_months, 2) if ytd_months > 0 else 0.0
        prior_monthly_rate = round(prior_year_amount / 12.0, 2)

        is_declining = (current_monthly_rate < prior_monthly_rate * 0.90)

        if is_declining:
            qualifying_monthly = current_monthly_rate
            notes = "Declining earnings trend detected (>10% drop); conservative current YTD monthly rate applied."
        else:
            qualifying_monthly = two_year_monthly_avg
            notes = "Stable/increasing trend; standard 24-month weighted average applied."

        return {
            "income_type": "variable_overtime_bonus",
            "prior_year_amount": prior_year_amount,
            "current_year_ytd_amount": current_year_ytd_amount,
            "ytd_months": ytd_months,
            "monthly_amount": qualifying_monthly,
            "is_declining_trend": is_declining,
            "notes": notes,
            "rule_citation": "Fannie Mae Form 1084 / Selling Guide B3-3.1-04"
        }

    @classmethod
    def validate_urla_field_staging(cls, section_name: str, field_name: str) -> None:
        """
        Enforces strict attestation guard:
        AI Agents are legally forbidden from staging or answering URLA Sections 5, 6, 7, 8.
        """
        sec = section_name.lower().strip()
        if sec in cls.FORBIDDEN_URLA_SECTIONS or "declaration" in sec or "demographic" in sec:
            raise PermissionError(
                f"FORBIDDEN_ATTESTATION: AI agents cannot stage or answer fields in URLA {section_name}. "
                f"Declarations and attestations must be executed exclusively by the borrower."
            )

    @classmethod
    def generate_needs_list(
        cls,
        program: str,
        indexed_document_types: List[str]
    ) -> List[Dict[str, str]]:
        """
        Evaluates current indexed document types against standard checklist for the loan program.
        Generates itemized missing needs list.
        """
        required_by_program = {
            "conv_30_fixed": [
                {"type": "paystub", "description": "Most recent 30 consecutive days paystubs"},
                {"type": "w2", "description": "W-2 forms for the past 2 calendar years"},
                {"type": "bank_statement", "description": "2 consecutive months full bank asset statements (all pages)"},
                {"type": "purchase_contract", "description": "Fully executed purchase and sale agreement"}
            ],
            "fha_30_fixed": [
                {"type": "paystub", "description": "Most recent 30 consecutive days paystubs"},
                {"type": "w2", "description": "W-2 forms for past 2 years"},
                {"type": "tax_return", "description": "Signed federal tax returns (Form 1040) past 2 years"},
                {"type": "bank_statement", "description": "2 consecutive months bank statements"}
            ]
        }

        checklist = required_by_program.get(program, required_by_program["conv_30_fixed"])
        missing = []

        existing_types = set(d.lower() for d in indexed_document_types)

        for req in checklist:
            if req["type"] not in existing_types:
                missing.append(req)

        return missing
