"""
DF-163 LexVance-Wegzugssteuer-Risiko-Tracker
Per-Client Wegzugssteuer-Deferral-Risk-Tracking — KEIN Legal-Advice, KEINE Steuer-Empfehlungen.
[CRUX-MK]
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DeferralCase:
    client_id: str
    client_name: str
    deferred_tax_eur: float
    deferral_start_date: str   # ISO date
    compliance_deadline: str   # ISO date
    status: str = "active"    # active | resolved | overdue
    notes: str = ""

    def deadline_days_remaining(self, reference_date: Optional[date] = None) -> int:
        ref = reference_date or date.today()
        return (date.fromisoformat(self.compliance_deadline) - ref).days

    def is_high_risk(self, reference_date: Optional[date] = None) -> bool:
        """High-risk: overdue OR fewer than 90 days to compliance deadline."""
        days = self.deadline_days_remaining(reference_date)
        return self.status == "overdue" or (self.status == "active" and days < 90)


@dataclass
class RiskReport:
    report_date: str
    active_deferrals_count: int
    total_deferred_tax_eur: float
    high_risk_cases_count: int
    compliance_deadline_aging: Dict[str, int]   # client_id -> days_remaining
    cases: List[dict]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class WegzugssteuerTracker:
    """
    Tracks Wegzugssteuer deferral risk indicators per client.
    Tracking only — no legal advice, no tax recommendations.
    """

    def __init__(self) -> None:
        self._cases: Dict[str, DeferralCase] = {}

    def add_case(self, case: DeferralCase) -> None:
        self._cases[case.client_id] = case

    def remove_case(self, client_id: str) -> bool:
        if client_id not in self._cases:
            return False
        del self._cases[client_id]
        return True

    def update_status(self, client_id: str, new_status: str) -> bool:
        if client_id not in self._cases:
            return False
        valid = {"active", "resolved", "overdue"}
        if new_status not in valid:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid}")
        self._cases[client_id].status = new_status
        return True

    def get_overdue_cases(self, reference_date: Optional[date] = None) -> List[DeferralCase]:
        ref = reference_date or date.today()
        return [
            c for c in self._cases.values()
            if c.status == "active" and c.deadline_days_remaining(ref) < 0
        ]

    def auto_mark_overdue(self, reference_date: Optional[date] = None) -> int:
        """Marks active cases past their deadline as overdue. Returns count updated."""
        updated = 0
        for case in self.get_overdue_cases(reference_date):
            case.status = "overdue"
            updated += 1
        return updated

    def generate_report(self, reference_date: Optional[date] = None) -> RiskReport:
        ref = reference_date or date.today()
        active = [c for c in self._cases.values() if c.status == "active"]
        high_risk = [c for c in self._cases.values() if c.is_high_risk(ref)]
        aging = {
            c.client_id: c.deadline_days_remaining(ref)
            for c in self._cases.values()
            if c.status in ("active", "overdue")
        }
        return RiskReport(
            report_date=ref.isoformat(),
            active_deferrals_count=len(active),
            total_deferred_tax_eur=sum(c.deferred_tax_eur for c in active),
            high_risk_cases_count=len(high_risk),
            compliance_deadline_aging=aging,
            cases=[asdict(c) for c in self._cases.values()],
        )

    def save_report(self, report: RiskReport, output_dir: str = "reports") -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        path = Path(output_dir) / f"df-163-{report.report_date}.json"
        path.write_text(report.to_json(), encoding="utf-8")
        return str(path)
# [CRUX-MK]
