from backend.services.slot_engine import find_available_slots
from backend.services.time_utils import (
    time_to_minutes,
    minutes_to_time,
)
from backend.optimization.priority import calculate_priority


def _select_exact_block(
    available_slot: dict,
    required_duration: int,
) -> tuple[str, str]:
    """
    Select the exact maintenance block from an available window.

    The available slot may be longer than the required maintenance
    duration. We use the beginning of the available window and reserve
    only the required duration.
    """

    slot_start_minutes = time_to_minutes(
        available_slot["start_time"]
    )

    slot_end_minutes = time_to_minutes(
        available_slot["end_time"]
    )

    selected_end_minutes = (
        slot_start_minutes + required_duration
    )

    if selected_end_minutes > slot_end_minutes:
        raise ValueError(
            "Required maintenance duration exceeds available slot."
        )

    return (
        minutes_to_time(slot_start_minutes),
        minutes_to_time(selected_end_minutes),
    )


def _is_block_compatible(
    block: dict,
    task: dict,
) -> bool:
    """
    Check whether an existing block can be used by a task.

    Compatibility requires:
    - Same section
    - Block is AVAILABLE
    - Block is approved for the task's department
    """

    if block.get("section_id") != task.get("section_id"):
        return False

    if block.get("block_status") not in {"AVAILABLE", "APPROVED"}:
        return False

    approved_department = block.get(
        "approved_for_department"
    )

    task_department = task.get(
        "department"
    )

    if not approved_department:
        return False

    return (
        str(approved_department).strip().upper()
        == str(task_department).strip().upper()
    )


def _overlaps_existing_maintenance(
    section_intervals: list[tuple[int, int]],
    candidate_start: int,
    candidate_end: int,
) -> bool:
    """
    Return True when a candidate maintenance block overlaps
    an already scheduled maintenance block on the same section.
    """

    for existing_start, existing_end in section_intervals:

        if (
            existing_start < candidate_end
            and existing_end > candidate_start
        ):
            return True

    return False


def _resources_conflict(
    task_1: dict,
    task_2: dict,
) -> bool:
    """
    Determine whether two tasks require the same resource
    combination.

    The current dataset stores required resources as a complete
    textual combination, for example:

        "6 workers, tamping machine"

    Identical normalized combinations are therefore treated as
    competing for the same resource.
    """

    resource_1 = str(
        task_1.get("required_resources", "")
    ).strip().lower()

    resource_2 = str(
        task_2.get("required_resources", "")
    ).strip().lower()

    if not resource_1 or not resource_2:
        return False

    return resource_1 == resource_2


def _resource_key(task: dict) -> str:
    """
    Return the normalized resource identifier for a task.
    """

    return str(
        task.get("required_resources", "")
    ).strip().lower()


def _resource_intervals_conflict(
    resource_intervals: list[tuple[int, int]],
    candidate_start: int,
    candidate_end: int,
) -> bool:
    """
    Return True when the candidate block overlaps a previously
    scheduled task using the same resource.
    """

    for existing_start, existing_end in resource_intervals:

        if (
            existing_start < candidate_end
            and existing_end > candidate_start
        ):
            return True

    return False


def _select_non_overlapping_slot(
    slots: list[dict],
    required_duration: int,
    scheduled_intervals: list[tuple[int, int]],
    resource_intervals: list[tuple[int, int]] | None = None,
) -> dict | None:
    """
    Select the earliest feasible exact maintenance block.

    A returned slot may be a large free window. If the beginning
    of that window is occupied by previously scheduled maintenance,
    move forward inside the same free window until a feasible block
    is found.

    A candidate is rejected when it overlaps either:
    - maintenance already scheduled on the same section
    - maintenance already using the same resource
    """

    if resource_intervals is None:
        resource_intervals = []

    for slot in slots:

        slot_start = time_to_minutes(
            slot["start_time"]
        )

        slot_end = time_to_minutes(
            slot["end_time"]
        )

        candidate_start = slot_start

        while (
            candidate_start + required_duration
            <= slot_end
        ):

            candidate_end = (
                candidate_start + required_duration
            )

            section_conflict = (
                _overlaps_existing_maintenance(
                    scheduled_intervals,
                    candidate_start,
                    candidate_end,
                )
            )

            resource_conflict = (
                _resource_intervals_conflict(
                    resource_intervals,
                    candidate_start,
                    candidate_end,
                )
            )

            if not section_conflict and not resource_conflict:

                return {
                    **slot,
                    "selected_start": minutes_to_time(
                        candidate_start
                    ),
                    "selected_end": minutes_to_time(
                        candidate_end
                    ),
                    "selected_duration": required_duration,
                }

            # Find the next time at which the candidate can
            # possibly become feasible.
            conflicting_end_times = []

            for existing_start, existing_end in scheduled_intervals:

                if (
                    existing_start < candidate_end
                    and existing_end > candidate_start
                ):
                    conflicting_end_times.append(
                        existing_end
                    )

            for existing_start, existing_end in resource_intervals:

                if (
                    existing_start < candidate_end
                    and existing_end > candidate_start
                ):
                    conflicting_end_times.append(
                        existing_end
                    )

            if not conflicting_end_times:
                break

            candidate_start = max(
                conflicting_end_times
            )

    return None


def _can_coordinate(
    tasks: list[dict],
) -> bool:
    """
    Determine whether tasks should share a common maintenance block.

    Tasks are coordinated only when:
    - They belong to different departments.
    - They do not require the same resource combination.
    """

    departments = {
        str(task.get("department", "")).strip().upper()
        for task in tasks
    }

    departments.discard("")

    if len(departments) <= 1:
        return False

    resources = []

    for task in tasks:

        resource = _resource_key(task)

        if resource:
            resources.append(resource)

    # Same resource combination means resource contention.
    if len(resources) != len(set(resources)):
        return False

    return True


def _build_coordination_groups(
    tasks: list[dict],
) -> list[list[dict]]:
    """
    Build groups of tasks that can safely share a maintenance block.

    Tasks can be coordinated when:
    - They belong to different departments.
    - They do not share the same required resource combination.

    Tasks that cannot be coordinated remain individual tasks.
    """

    groups = []

    for task in tasks:

        placed = False

        task_department = str(
            task.get("department", "")
        ).strip().upper()

        for group in groups:

            group_departments = {
                str(
                    existing_task.get("department", "")
                ).strip().upper()
                for existing_task in group
            }

            # Do not put two tasks from the same department
            # into the same coordinated block.
            if task_department in group_departments:
                continue

            # Do not put tasks using the same resource into
            # the same coordinated block.
            if any(
                _resources_conflict(
                    task,
                    existing_task,
                )
                for existing_task in group
            ):
                continue

            group.append(task)
            placed = True
            break

        if not placed:
            groups.append([task])

    return groups


def optimize_maintenance(
    maintenance_tasks: list[dict],
    trains: list[dict],
    existing_blocks: list[dict] | None = None,
) -> dict:
    """
    Generate an optimized maintenance schedule.

    Tasks are prioritized first.

    Tasks belonging to the same section may be coordinated when
    they belong to different departments and do not compete for
    the same required resources.

    Existing approved/available blocks are preferred whenever
    they can accommodate the maintenance task without conflicting
    with train movements.

    Non-coordinated maintenance tasks are prevented from
    overlapping on the same section.

    Resource conflicts are also prevented across sections.
    """

    if existing_blocks is None:
        existing_blocks = []

    # ---------------------------------------------------------
    # 1. Calculate priority for every task
    # ---------------------------------------------------------

    prioritized_tasks = []

    for task in maintenance_tasks:

        priority = calculate_priority(task)

        task_with_priority = {
            **task,
            **priority,
        }

        prioritized_tasks.append(
            task_with_priority
        )

    # Highest priority first
    prioritized_tasks.sort(
        key=lambda task: task["priority_score"],
        reverse=True,
    )

    assignments = []
    unscheduled = []

    # ---------------------------------------------------------
    # 2. Track maintenance already scheduled by section
    # ---------------------------------------------------------

    scheduled_intervals_by_section = {}

    # ---------------------------------------------------------
    # 3. Track resources already scheduled
    # ---------------------------------------------------------

    scheduled_intervals_by_resource = {}

    # ---------------------------------------------------------
    # 4. Group tasks by section
    # ---------------------------------------------------------

    section_groups = {}

    for task in prioritized_tasks:

        section_id = task["section_id"]

        if section_id not in section_groups:
            section_groups[section_id] = []

        section_groups[section_id].append(task)

    # ---------------------------------------------------------
    # 5. Process each section
    # ---------------------------------------------------------

    for section_id, tasks in section_groups.items():

        coordination_groups = _build_coordination_groups(
            tasks
        )

        # -----------------------------------------------------
        # 5A. Process each possible coordination group
        # -----------------------------------------------------

        for coordination_group in coordination_groups:

            should_coordinate = _can_coordinate(
                coordination_group
            )

            if should_coordinate:

                common_duration = max(
                    task["estimated_duration_minutes"]
                    for task in coordination_group
                )

                slots = find_available_slots(
                    maintenance_section=section_id,
                    duration_minutes=common_duration,
                    trains=trains,
                    existing_blocks=existing_blocks,
                )

                if slots:

                    section_intervals = (
                        scheduled_intervals_by_section.setdefault(
                            section_id,
                            [],
                        )
                    )

                    # A coordination group contains multiple
                    # resource combinations. Check all of them.
                    group_resource_intervals = []

                    for task in coordination_group:

                        resource = _resource_key(task)

                        if not resource:
                            continue

                        resource_intervals = (
                            scheduled_intervals_by_resource.get(
                                resource,
                                [],
                            )
                        )

                        group_resource_intervals.extend(
                            resource_intervals
                        )

                    selected_slot = (
                        _select_non_overlapping_slot(
                            slots=slots,
                            required_duration=common_duration,
                            scheduled_intervals=section_intervals,
                            resource_intervals=group_resource_intervals,
                        )
                    )

                    if selected_slot is not None:

                        block_start = selected_slot[
                            "selected_start"
                        ]

                        block_end = selected_slot[
                            "selected_end"
                        ]

                        coordinated_task_ids = [
                            task["request_id"]
                            for task in coordination_group
                        ]

                        block_start_minutes = time_to_minutes(
                            block_start
                        )

                        block_end_minutes = time_to_minutes(
                            block_end
                        )

                        for task in coordination_group:

                            assignments.append(
                                {
                                    "task_id": task["request_id"],
                                    "department": task["department"],
                                    "section_id": task["section_id"],
                                    "block_start": block_start,
                                    "block_end": block_end,
                                    "block_duration_minutes": (
                                        common_duration
                                    ),
                                    "task_duration_minutes": (
                                        task[
                                            "estimated_duration_minutes"
                                        ]
                                    ),
                                    "priority_score": (
                                        task["priority_score"]
                                    ),
                                    "priority": task["priority"],
                                    "coordination": True,
                                    "coordinated_tasks": (
                                        coordinated_task_ids
                                    ),
                                    "existing_block": (
                                        selected_slot.get(
                                            "existing_block",
                                            False,
                                        )
                                    ),
                                    "block_calendar_id": (
                                        selected_slot.get(
                                            "block_calendar_id"
                                        )
                                    ),
                                    "status": "RECOMMENDED",
                                }
                            )

                            resource = _resource_key(task)

                            if resource:

                                resource_intervals = (
                                    scheduled_intervals_by_resource.setdefault(
                                        resource,
                                        [],
                                    )
                                )

                                resource_intervals.append(
                                    (
                                        block_start_minutes,
                                        block_end_minutes,
                                    )
                                )

                        section_intervals.append(
                            (
                                block_start_minutes,
                                block_end_minutes,
                            )
                        )

                        continue

            # -------------------------------------------------
            # 5B. Schedule individual task(s)
            # -------------------------------------------------

            for task in coordination_group:

                required_duration = task[
                    "estimated_duration_minutes"
                ]

                individual_slots = find_available_slots(
                    maintenance_section=task["section_id"],
                    duration_minutes=required_duration,
                    trains=trains,
                    existing_blocks=existing_blocks,
                )

                if not individual_slots:

                    unscheduled.append(
                        {
                            "task_id": task["request_id"],
                            "reason": (
                                "No feasible maintenance "
                                "slot found."
                            ),
                        }
                    )

                    continue

                section_intervals = (
                    scheduled_intervals_by_section.setdefault(
                        task["section_id"],
                        [],
                    )
                )

                resource = _resource_key(task)

                resource_intervals = (
                    scheduled_intervals_by_resource.setdefault(
                        resource,
                        [],
                    )
                    if resource
                    else []
                )

                selected_slot = _select_non_overlapping_slot(
                    slots=individual_slots,
                    required_duration=required_duration,
                    scheduled_intervals=section_intervals,
                    resource_intervals=resource_intervals,
                )

                if selected_slot is None:

                    unscheduled.append(
                        {
                            "task_id": task["request_id"],
                            "reason": (
                                "No feasible non-overlapping "
                                "maintenance slot found."
                            ),
                        }
                    )

                    continue

                block_start = selected_slot[
                    "selected_start"
                ]

                block_end = selected_slot[
                    "selected_end"
                ]

                block_start_minutes = time_to_minutes(
                    block_start
                )

                block_end_minutes = time_to_minutes(
                    block_end
                )

                assignments.append(
                    {
                        "task_id": task["request_id"],
                        "department": task["department"],
                        "section_id": task["section_id"],
                        "block_start": block_start,
                        "block_end": block_end,
                        "block_duration_minutes": (
                            required_duration
                        ),
                        "task_duration_minutes": (
                            required_duration
                        ),
                        "priority_score": (
                            task["priority_score"]
                        ),
                        "priority": task["priority"],
                        "coordination": False,
                        "coordinated_tasks": [],
                        "existing_block": selected_slot.get(
                            "existing_block",
                            False,
                        ),
                        "block_calendar_id": selected_slot.get(
                            "block_calendar_id"
                        ),
                        "status": "RECOMMENDED",
                    }
                )

                section_intervals.append(
                    (
                        block_start_minutes,
                        block_end_minutes,
                    )
                )

                if resource:

                    resource_intervals.append(
                        (
                            block_start_minutes,
                            block_end_minutes,
                        )
                    )

    return {
        "assignments": assignments,
        "unscheduled": unscheduled,
    }