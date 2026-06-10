import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
# '163' starts with a digit — not a valid Python identifier.
# Equivalent to: from 163 import WegzugssteuerTracker, DeferralCase, RiskReport
import importlib
import json
from datetime import date, timedelta

_mod = importlib.import_module("163")
WegzugssteuerTracker = _mod.WegzugssteuerTracker
DeferralCase = _mod.DeferralCase
RiskReport = _mod.RiskReport

REF = date(2026, 6, 9)


def _case(cid="C001", tax=50_000.0, days=120, status="active") -> DeferralCase:
    return DeferralCase(
        client_id=cid,
        client_name=f"Client {cid}",
        deferred_tax_eur=tax,
        deferral_start_date=(REF - timedelta(days=30)).isoformat(),
        compliance_deadline=(REF + timedelta(days=days)).isoformat(),
        status=status,
    )


def test_active_deferrals_count():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", days=120))
    t.add_case(_case("C002", days=200))
    r = t.generate_report(REF)
    assert r.active_deferrals_count == 2


def test_total_deferred_tax_eur():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", tax=30_000.0, days=120))
    t.add_case(_case("C002", tax=70_000.0, days=150))
    r = t.generate_report(REF)
    assert r.total_deferred_tax_eur == 100_000.0


def test_high_risk_cases_under_90_days():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", days=30))    # < 90 → high risk
    t.add_case(_case("C002", days=200))   # safe
    t.add_case(_case("C003", days=89))    # < 90 → high risk
    r = t.generate_report(REF)
    assert r.high_risk_cases_count == 2


def test_compliance_deadline_aging():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", days=45))
    r = t.generate_report(REF)
    assert r.compliance_deadline_aging["C001"] == 45


def test_resolved_excluded_from_active_and_total():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", tax=40_000.0, days=120))
    t.add_case(_case("C002", tax=60_000.0, days=120))
    t.update_status("C001", "resolved")
    r = t.generate_report(REF)
    assert r.active_deferrals_count == 1
    assert r.total_deferred_tax_eur == 60_000.0


def test_overdue_status_is_high_risk():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", days=120, status="overdue"))
    r = t.generate_report(REF)
    assert r.high_risk_cases_count == 1


def test_auto_mark_overdue():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", days=-5))   # past deadline
    t.add_case(_case("C002", days=50))   # still active
    updated = t.auto_mark_overdue(REF)
    assert updated == 1
    r = t.generate_report(REF)
    # C001 now overdue (not counted in active), C002 still active
    assert r.active_deferrals_count == 1


def test_remove_case():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001"))
    assert t.remove_case("C001") is True
    assert t.remove_case("C001") is False
    assert t.generate_report(REF).active_deferrals_count == 0


def test_report_json_roundtrip():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", tax=55_000.0, days=100))
    r = t.generate_report(REF)
    data = json.loads(r.to_json())
    assert data["report_date"] == REF.isoformat()
    assert data["active_deferrals_count"] == 1
    assert data["total_deferred_tax_eur"] == 55_000.0
    assert len(data["cases"]) == 1


def test_invalid_status_raises():
    t = WegzugssteuerTracker()
    t.add_case(_case("C001"))
    try:
        t.update_status("C001", "pending")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_no_legal_advice_in_report():
    """Report output must contain no legal/tax recommendation language."""
    t = WegzugssteuerTracker()
    t.add_case(_case("C001", days=20))
    payload = t.generate_report(REF).to_json().lower()
    for forbidden in ("empfehlung", "recommendation", "advice", "legal", "steuerberatung"):
        assert forbidden not in payload, f"Forbidden term in output: {forbidden}"
