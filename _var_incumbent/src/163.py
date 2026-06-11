from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value in (None, ""):
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _to_eur(value: Any) -> float:
    return round(float(value or 0.0), 2)


def classify_deadline(days_to_deadline: Optional[int]) -> str:
    if days_to_deadline is None:
        return "no_deadline"
    if days_to_deadline < 0:
        return "overdue"
    if days_to_deadline <= 30:
        return "due_0_30_days"
    if days_to_deadline <= 90:
        return "due_31_90_days"
    return "due_91_plus_days"


def is_high_risk_case(
    case: Dict[str, Any],
    *,
    days_to_deadline: Optional[int],
    high_risk_tax_threshold_eur: float = 100000.0,
) -> bool:
    if not case.get("deferral_active", False):
        return False
    if case.get("manual_high_risk", False):
        return True
    if _to_eur(case.get("deferred_tax_eur")) >= high_risk_tax_threshold_eur:
        return True
    if days_to_deadline is not None and days_to_deadline < 0:
        return True
    return False


def compute_risk_report(
    cases: Iterable[Dict[str, Any]],
    *,
    today: Optional[str] = None,
    high_risk_tax_threshold_eur: float = 100000.0,
) -> Dict[str, Any]:
    today_date = _parse_date(today) if today else date.today()

    processed_cases: List[Dict[str, Any]] = []
    active_deferrals_count = 0
    total_deferred_tax_eur = 0.0
    high_risk_cases_count = 0
    aging = {
        "overdue": 0,
        "due_0_30_days": 0,
        "due_31_90_days": 0,
        "due_91_plus_days": 0,
        "no_deadline": 0,
    }

    for raw_case in cases:
        case = dict(raw_case)
        deferred_tax_eur = _to_eur(case.get("deferred_tax_eur"))
        deadline = _parse_date(case.get("compliance_deadline"))
        days_to_deadline = None if deadline is None else (deadline - today_date).days
        aging_bucket = classify_deadline(days_to_deadline)
        high_risk = is_high_risk_case(
            case,
            days_to_deadline=days_to_deadline,
            high_risk_tax_threshold_eur=high_risk_tax_threshold_eur,
        )

        if case.get("deferral_active", False):
            active_deferrals_count += 1
            total_deferred_tax_eur += deferred_tax_eur
            aging[aging_bucket] += 1
            if high_risk:
                high_risk_cases_count += 1

        processed_cases.append(
            {
                "client_id": case.get("client_id"),
                "deferral_active": bool(case.get("deferral_active", False)),
                "deferred_tax_eur": deferred_tax_eur,
                "compliance_deadline": case.get("compliance_deadline"),
                "days_to_deadline": days_to_deadline,
                "deadline_bucket": aging_bucket,
                "high_risk": high_risk,
            }
        )

    return {
        "report_date": today_date.isoformat(),
        "summary": {
            "active_deferrals_count": active_deferrals_count,
            "total_deferred_tax_eur": round(total_deferred_tax_eur, 2),
            "high_risk_cases_count": high_risk_cases_count,
            "compliance_deadline_aging": aging,
        },
        "cases": processed_cases,
    }
# [CRUX-MK]
