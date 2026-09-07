from backend.optimization.optimizer import optimize_maintenance


def test_same_section_tasks_are_coordinated():

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
        {
            "request_id": "TDMS-001",
            "department": "TRACTION",
            "section_id": "SEC01",
            "estimated_duration_minutes": 90,
            "defect_severity": "HIGH",
            "failure_risk": "HIGH",
            "safety_related": True,
            "asset_operational_status": "RESTRICTED",
            "overdue": False,
        },
    ]

    trains = [
        {
            "train_id": "TRAIN-001",
            "section_id": "SEC01",
            "start_time": "04:00",
            "end_time": "05:00",
        }
    ]

    result = optimize_maintenance(
        maintenance_tasks,
        trains,
    )

    assert len(result["assignments"]) == 3

    starts = {
        assignment["block_start"]
        for assignment in result["assignments"]
    }

    ends = {
        assignment["block_end"]
        for assignment in result["assignments"]
    }

    assert len(starts) == 1
    assert len(ends) == 1

    for assignment in result["assignments"]:
        assert assignment["coordination"] is True
        assert len(assignment["coordinated_tasks"]) == 3