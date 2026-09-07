from backend.optimization.priority import (
    calculate_priority_score,
    classify_priority,
    calculate_priority,
)


def test_critical_safety_overdue_task_gets_high_score():

    task = {
        "request_id": "TMS-001",
        "defect_severity": "CRITICAL",
        "failure_risk": "HIGH",
        "safety_related": True,
        "asset_operational_status": "RESTRICTED",
        "overdue": True,
    }

    score = calculate_priority_score(task)

    assert score == 78


def test_low_priority_task():

    task = {
        "request_id": "TMS-002",
        "defect_severity": "LOW",
        "failure_risk": "LOW",
        "safety_related": False,
        "asset_operational_status": "OPERATIONAL",
        "overdue": False,
    }

    score = calculate_priority_score(task)

    assert score == 8


def test_priority_classification():

    assert classify_priority(90) == "CRITICAL"
    assert classify_priority(70) == "HIGH"
    assert classify_priority(50) == "MEDIUM"
    assert classify_priority(20) == "LOW"


def test_complete_priority_result():

    task = {
        "request_id": "SMMS-001",
        "defect_severity": "HIGH",
        "failure_risk": "HIGH",
        "safety_related": True,
        "asset_operational_status": "RESTRICTED",
        "overdue": False,
    }

    result = calculate_priority(task)

    assert result["task_id"] == "SMMS-001"
    assert result["priority_score"] == 63
    assert result["priority"] == "HIGH"