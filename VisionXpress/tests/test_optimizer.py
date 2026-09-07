from backend.optimization.optimizer import optimize_maintenance


def test_optimizer_assigns_feasible_slot():

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
        }
    ]

    trains = [
        {
            "train_id": "T001",
            "section_id": "SEC01",
            "start_time": "02:00",
            "end_time": "03:00",
        }
    ]

    result = optimize_maintenance(
        maintenance_tasks,
        trains,
    )

    assert len(result["assignments"]) == 1

    assignment = result["assignments"][0]

    assert assignment["task_id"] == "TMS-001"
    assert assignment["block_start"] == "00:00"
    assert assignment["block_end"] == "02:00"
    assert assignment["priority"] == "HIGH"


def test_optimizer_prioritizes_critical_task():

    maintenance_tasks = [
        {
            "request_id": "LOW-001",
            "department": "ENGINEERING",
            "section_id": "SEC01",
            "estimated_duration_minutes": 60,
            "defect_severity": "LOW",
            "failure_risk": "LOW",
            "safety_related": False,
            "asset_operational_status": "OPERATIONAL",
            "overdue": False,
        },
        {
            "request_id": "CRITICAL-001",
            "department": "SMMS",
            "section_id": "SEC01",
            "estimated_duration_minutes": 60,
            "defect_severity": "CRITICAL",
            "failure_risk": "HIGH",
            "safety_related": True,
            "asset_operational_status": "RESTRICTED",
            "overdue": True,
        },
    ]

    trains = []

    result = optimize_maintenance(
        maintenance_tasks,
        trains,
    )

    assert result["assignments"][0]["task_id"] == "CRITICAL-001"


def test_optimizer_unschedules_when_no_slot_exists():

    maintenance_tasks = [
        {
            "request_id": "TMS-002",
            "department": "ENGINEERING",
            "section_id": "SEC01",
            "estimated_duration_minutes": 120,
            "defect_severity": "HIGH",
            "failure_risk": "HIGH",
            "safety_related": True,
            "asset_operational_status": "RESTRICTED",
            "overdue": False,
        }
    ]

    trains = [
        {
            "train_id": "T001",
            "section_id": "SEC01",
            "start_time": "00:00",
            "end_time": "23:59",
        }
    ]

    result = optimize_maintenance(
        maintenance_tasks,
        trains,
    )

    assert len(result["assignments"]) == 0
    assert len(result["unscheduled"]) == 1