from collections import defaultdict

from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_maintenance_tasks,
    normalize_trains,
    normalize_existing_blocks,
)
from backend.services.planning_engine import generate_block_plan


def test_resource_overlap_diagnostics():

    # ---------------------------------------------------------
    # 1. Load real data
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

    planning_date = "2026-09-01"

    # ---------------------------------------------------------
    # 2. Generate schedule
    # ---------------------------------------------------------

    result = generate_block_plan(
        maintenance_tasks=tasks,
        trains=trains,
        existing_blocks=existing_blocks,
        planning_date=planning_date,
    )

    assignments = result["optimization"]["assignments"]

    # ---------------------------------------------------------
    # 3. Map task ID -> required resources
    # ---------------------------------------------------------

    task_resources = {
        task["request_id"]: str(
            task.get("required_resources", "")
        ).strip()
        for task in tasks
    }

    # ---------------------------------------------------------
    # 4. Group assignments by resource combination
    # ---------------------------------------------------------

    resource_assignments = defaultdict(list)

    for assignment in assignments:

        resource = task_resources.get(
            assignment["task_id"],
            "",
        )

        if not resource:
            continue

        resource_assignments[resource].append(
            assignment
        )

    # ---------------------------------------------------------
    # 5. Find overlapping assignments using same resource
    # ---------------------------------------------------------

    overlaps = []

    for resource, resource_tasks in resource_assignments.items():

        for i in range(len(resource_tasks)):

            first = resource_tasks[i]

            first_start = first["block_start"]
            first_end = first["block_end"]

            for j in range(i + 1, len(resource_tasks)):

                second = resource_tasks[j]

                second_start = second["block_start"]
                second_end = second["block_end"]

                # Convert HH:MM to minutes
                first_start_minutes = (
                    int(first_start[:2]) * 60
                    + int(first_start[3:])
                )

                first_end_minutes = (
                    int(first_end[:2]) * 60
                    + int(first_end[3:])
                )

                second_start_minutes = (
                    int(second_start[:2]) * 60
                    + int(second_start[3:])
                )

                second_end_minutes = (
                    int(second_end[:2]) * 60
                    + int(second_end[3:])
                )

                if (
                    first_start_minutes < second_end_minutes
                    and first_end_minutes > second_start_minutes
                ):

                    overlaps.append(
                        {
                            "resource": resource,
                            "task_1": first["task_id"],
                            "task_2": second["task_id"],
                            "time_1": (
                                f"{first_start} -> {first_end}"
                            ),
                            "time_2": (
                                f"{second_start} -> {second_end}"
                            ),
                        }
                    )

    # ---------------------------------------------------------
    # 6. Print diagnostic report
    # ---------------------------------------------------------

    print("\n")
    print("=" * 80)
    print("VISIONXPRESS RESOURCE OVERLAP DIAGNOSTICS")
    print("=" * 80)

    print(f"Scheduled tasks: {len(assignments)}")
    print(
        f"Resource combinations used: "
        f"{len(resource_assignments)}"
    )

    print("\n")
    print("RESOURCE USAGE")
    print("-" * 80)

    for resource, resource_tasks in sorted(
        resource_assignments.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    ):

        print(
            f"{resource:45} "
            f"assignments={len(resource_tasks)}"
        )

    print("\n")
    print("RESOURCE OVERLAPS")
    print("-" * 80)

    if not overlaps:

        print("No overlapping assignments detected.")

    else:

        for overlap in overlaps:

            print(
                f"{overlap['resource']}\n"
                f"    {overlap['task_1']:15} "
                f"{overlap['time_1']}\n"
                f"    {overlap['task_2']:15} "
                f"{overlap['time_2']}\n"
            )

    print("\n")
    print(
        f"Total resource overlaps: {len(overlaps)}"
    )

    assert len(assignments) > 0