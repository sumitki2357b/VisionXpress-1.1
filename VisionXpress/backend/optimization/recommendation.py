def build_recommendation(assignments: list[dict]) -> dict:
    """
    Convert optimizer assignments into a BDMS-style recommendation.
    """

    if not assignments:
        return {
            "status": "NO_RECOMMENDATION",
            "message": "No feasible maintenance block found.",
            "recommended_block": None,
            "tasks": [],
            "coordination": {
                "enabled": False,
                "departments": [],
                "task_count": 0,
            },
        }

    first = assignments[0]

    departments = sorted(
        {
            assignment["department"]
            for assignment in assignments
        }
    )

    task_ids = [
        assignment["task_id"]
        for assignment in assignments
    ]

    coordinated = any(
        assignment.get("coordination", False)
        for assignment in assignments
    )

    return {
        "status": "RECOMMENDED",
        "message": (
            "Maintenance block recommended based on "
            "train conflict analysis, priority and coordination."
        ),
        "recommended_block": {
            "section_id": first["section_id"],
            "start_time": first["block_start"],
            "end_time": first["block_end"],
            "duration_minutes": first["block_duration_minutes"],
        },
        "tasks": assignments,
        "coordination": {
            "enabled": coordinated,
            "departments": departments,
            "task_count": len(assignments),
        },
        "bdms_action": {
            "options": [
                "ACCEPT",
                "DECLINE",
                "REQUEST_BETTERMENT",
                "MODIFY",
            ],
            "status": "PENDING_BDMS_APPROVAL",
        },
    }