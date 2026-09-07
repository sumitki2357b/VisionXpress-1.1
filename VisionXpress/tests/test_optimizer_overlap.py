from backend.optimization.optimizer import optimize_maintenance


def test_optimizer_avoids_non_coordinated_maintenance_overlap():

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
            "request_id": "TMS-002",
            "department": "ENGINEERING",
            "section_id": "SEC01",
            "estimated_duration_minutes": 120,
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
        },
        {
            "train_id": "TRAIN-002",
            "section_id": "SEC01",
            "start_time": "09:00",
            "end_time": "10:00",
        },
    ]

    result = optimize_maintenance(
        maintenance_tasks=maintenance_tasks,
        trains=trains,
        existing_blocks=[],
    )

    assignments = result["assignments"]

    assert len(assignments) == 2

    first = assignments[0]
    second = assignments[1]

    assert first["block_start"] == "05:00"
    assert first["block_end"] == "07:00"

    assert second["block_start"] == "07:00"
    assert second["block_end"] == "09:00"

    assert not (
        first["block_start"] == second["block_start"]
        and first["block_end"] == second["block_end"]
    )