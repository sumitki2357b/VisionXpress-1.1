from backend.optimization.optimizer import optimize_maintenance


def test_optimizer_reuses_existing_block():

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
            "train_id": "TRAIN-001",
            "section_id": "SEC01",
            "start_time": "00:00",
            "end_time": "05:00",
        }
    ]

    existing_blocks = [
        {
            "block_calendar_id": "BLOCK-001",
            "section_id": "SEC01",
            "block_date": "2026-08-30",
            "start_time": "05:00",
            "end_time": "07:00",
            "approved_for_department": "ENGINEERING",
            "block_status": "AVAILABLE",
        }
    ]

    result = optimize_maintenance(
        maintenance_tasks=maintenance_tasks,
        trains=trains,
        existing_blocks=existing_blocks,
    )

    assert len(result["assignments"]) == 1

    assignment = result["assignments"][0]

    assert assignment["block_start"] == "05:00"
    assert assignment["block_end"] == "07:00"

    assert assignment["existing_block"] is True

    assert assignment["block_calendar_id"] == "BLOCK-001"