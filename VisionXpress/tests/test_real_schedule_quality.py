from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_maintenance_tasks,
    normalize_trains,
    normalize_existing_blocks,
    normalize_section_master,
)
from backend.services.planning_engine import generate_block_plan


def test_real_schedule_quality():

    # ---------------------------------------------------------
    # 1. Load real Excel data
    # ---------------------------------------------------------

    data = load_all_data()

    tasks = normalize_maintenance_tasks(
        data["tms"],
        data["tdms"],
        data["smms"],
    )

    trains = normalize_trains(
        data["coa"]
    )

    existing_blocks = normalize_existing_blocks(
        data["existing_blocks"]
    )

    sections = normalize_section_master(
        data["section_master"]
    )

    # ---------------------------------------------------------
    # 2. Generate real schedule
    # ---------------------------------------------------------

    planning_date = "2026-09-01"

    result = generate_block_plan(
        maintenance_tasks=tasks,
        trains=trains,
        existing_blocks=existing_blocks,
        planning_date=planning_date,
    )

    optimization = result["optimization"]

    assignments = optimization["assignments"]
    unscheduled = optimization["unscheduled"]

    # ---------------------------------------------------------
    # 3. Basic data summary
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("VISIONXPRESS REAL SCHEDULE REPORT")
    print("=" * 70)

    print(f"Planning date       : {planning_date}")
    print(f"Maintenance tasks   : {len(tasks)}")
    print(f"Trains              : {len(trains)}")
    print(f"Existing blocks     : {len(existing_blocks)}")
    print(f"Sections            : {len(sections)}")

    # ---------------------------------------------------------
    # 4. Filtered planning data summary
    # ---------------------------------------------------------

    input_summary = result.get(
        "input_summary",
        {}
    )

    print("\n")
    print("FILTERED PLANNING DATA")
    print("-" * 70)

    print(
        "Eligible tasks      :",
        input_summary.get(
            "maintenance_tasks",
            "NOT AVAILABLE",
        )
    )

    print(
        "Filtered trains     :",
        input_summary.get(
            "trains",
            "NOT AVAILABLE",
        )
    )

    print(
        "Filtered blocks     :",
        input_summary.get(
            "existing_blocks",
            "NOT AVAILABLE",
        )
    )

    # ---------------------------------------------------------
    # 5. Schedule summary
    # ---------------------------------------------------------

    print("\n")
    print("SCHEDULE SUMMARY")
    print("-" * 70)

    print(f"Scheduled tasks     : {len(assignments)}")
    print(f"Unscheduled tasks   : {len(unscheduled)}")

    # ---------------------------------------------------------
    # 6. Existing block usage
    # ---------------------------------------------------------

    existing_block_assignments = [
        assignment
        for assignment in assignments
        if assignment.get("existing_block") is True
    ]

    print(
        f"Existing blocks used: "
        f"{len(existing_block_assignments)}"
    )

    # ---------------------------------------------------------
    # 7. Coordination
    # ---------------------------------------------------------

    coordinated_assignments = [
        assignment
        for assignment in assignments
        if assignment.get("coordination") is True
    ]

    print(
        f"Coordinated tasks   : "
        f"{len(coordinated_assignments)}"
    )

    # ---------------------------------------------------------
    # 8. Print assignments
    # ---------------------------------------------------------

    print("\n")
    print("ASSIGNMENTS")
    print("-" * 70)

    for assignment in assignments:

        print(
            f"{assignment['task_id']:15} "
            f"{assignment['department']:15} "
            f"{assignment['section_id']:10} "
            f"{assignment['block_start']} -> "
            f"{assignment['block_end']} "
            f"| priority={assignment['priority']} "
            f"| score={assignment['priority_score']} "
            f"| existing={assignment.get('existing_block', False)} "
            f"| coordinated={assignment.get('coordination', False)}"
        )

    # ---------------------------------------------------------
    # 9. Print unscheduled tasks
    # ---------------------------------------------------------

    print("\n")
    print("UNSCHEDULED TASKS")
    print("-" * 70)

    for task in unscheduled:

        print(
            f"{task['task_id']:15} "
            f"| {task['reason']}"
        )

    # ---------------------------------------------------------
    # 10. Basic correctness checks
    # ---------------------------------------------------------

    assert result["planning_date"] == planning_date

    assert "optimization" in result
    assert "recommendation" in result

    assert "assignments" in optimization
    assert "unscheduled" in optimization

    # ---------------------------------------------------------
    # 11. Verify planning-date filtering
    # ---------------------------------------------------------

    assert input_summary["trains"] == 131

    assert input_summary["existing_blocks"] == 0

    assert input_summary["maintenance_tasks"] > 0

    # Every assignment must contain the core scheduling fields.
    for assignment in assignments:

        assert assignment["task_id"]
        assert assignment["department"]
        assert assignment["section_id"]
        assert assignment["block_start"]
        assert assignment["block_end"]
        assert assignment["task_duration_minutes"] > 0
        assert assignment["status"] == "RECOMMENDED"

    # ---------------------------------------------------------
    # 12. Final result
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("REAL SCHEDULE QUALITY CHECK PASSED")
    print("=" * 70) 