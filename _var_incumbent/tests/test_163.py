import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import importlib

m = importlib.import_module("163")
compute_risk_report = m.compute_risk_report
classify_deadline = m.classify_deadline
is_high_risk_case = m.is_high_risk_case


def test_compute_risk_report_tracks_core_metrics():
    cases = [
        {
            "client_id": "A-001",
            "deferral_active": True,
            "deferred_tax_eur": 125000,
            "compliance_deadline": "2026-06-05",
        },
        {
            "client_id": "B-002",
            "deferral_active": True,
            "deferred_tax_eur": 45000,
            "compliance_deadline": "2026-06-25",
        },
        {
            "client_id": "C-003",
            "deferral_active": True,
            "deferred_tax_eur": 7000,
            "compliance_deadline": None,
            "manual_high_risk": True,
        },
        {
            "client_id": "D-004",
            "deferral_active": False,
            "deferred_tax_eur": 999999,
            "compliance_deadline": "2026-06-01",
            "manual_high_risk": True,
        },
    ]

    report = compute_risk_report(cases, today="2026-06-10")

    assert report["report_date"] == "2026-06-10"
    assert report["summary"]["active_deferrals_count"] == 3
    assert report["summary"]["total_deferred_tax_eur"] == 177000.0
    assert report["summary"]["high_risk_cases_count"] == 2
    assert report["summary"]["compliance_deadline_aging"] == {
        "overdue": 1,
        "due_0_30_days": 1,
        "due_31_90_days": 0,
        "due_91_plus_days": 0,
        "no_deadline": 1,
    }

    by_id = {case["client_id"]: case for case in report["cases"]}

    assert by_id["A-001"]["days_to_deadline"] == -5
    assert by_id["A-001"]["deadline_bucket"] == "overdue"
    assert by_id["A-001"]["high_risk"] is True

    assert by_id["B-002"]["days_to_deadline"] == 15
    assert by_id["B-002"]["deadline_bucket"] == "due_0_30_days"
    assert by_id["B-002"]["high_risk"] is False

    assert by_id["C-003"]["days_to_deadline"] is None
    assert by_id["C-003"]["deadline_bucket"] == "no_deadline"
    assert by_id["C-003"]["high_risk"] is True

    assert by_id["D-004"]["high_risk"] is False


def test_helpers_cover_bucket_and_risk_rules():
    assert classify_deadline(None) == "no_deadline"
    assert classify_deadline(-1) == "overdue"
    assert classify_deadline(0) == "due_0_30_days"
    assert classify_deadline(45) == "due_31_90_days"
    assert classify_deadline(120) == "due_91_plus_days"

    assert is_high_risk_case(
        {"deferral_active": True, "deferred_tax_eur": 100000},
        days_to_deadline=10,
    ) is True
    assert is_high_risk_case(
        {"deferral_active": True, "deferred_tax_eur": 10},
        days_to_deadline=-1,
    ) is True
    assert is_high_risk_case(
        {"deferral_active": True, "deferred_tax_eur": 10, "manual_high_risk": True},
        days_to_deadline=10,
    ) is True
    assert is_high_risk_case(
        {"deferral_active": False, "deferred_tax_eur": 999999, "manual_high_risk": True},
        days_to_deadline=-10,
    ) is False

