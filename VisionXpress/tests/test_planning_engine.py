from backend.services.planning_engine import generate_block_plan


def test_generate_block_plan():

    maintenance_tasks = [
        {
            "request_id": "TMS-001",
            "department": "ENGINEERING",
            "section_id": "SEC01",
            "estimated_duration_minutes": 120,
            "defect_severity": "CRITICAL",
            "failure_risk": "HIGH",
            "safety_related": True,
            "asset_operational_status": "RESTRICTED",
            "overdue": True,
        },
        {
            "request_id": "SMMS-001",
            "department": "SIGNAL",
            "section_id": "SEC01",
            "estimated_duration_minutes": 60,
            "defect_severity": "MEDIUM",
            "failure_risk": "MEDIUM",
            "safety_related": False,
            "asset_operational_status": "NORMAL",
            "overdue": False,
        },
    ]

    trains = [
    {
        "train_id": "TRAIN-001",
        "section_id": "SEC01",
        "start_time": "00:00",
        "end_time": "05:00",
    }
    ]

    result = generate_block_plan(
        maintenance_tasks,
        trains,
    )

    assert "optimization" in result
    assert "recommendation" in result

    assert len(
        result["optimization"]["assignments"]
    ) == 2

    recommendation = result["recommendation"]

    assert recommendation["status"] == "RECOMMENDED"

    assert (
        recommendation["recommended_block"]["section_id"]
        == "SEC01"
    )

    assert (
        recommendation["recommended_block"]["start_time"]
        == "05:00"
    )

    assert (
        recommendation["recommended_block"]["end_time"]
        == "07:00"
    )

    assert recommendation["coordination"]["enabled"] is True