from backend.optimization.optimizer import optimize_maintenance
from backend.optimization.recommendation import build_recommendation


def _normalize_date(value) -> str | None:
    """
    Convert a date value into a comparable YYYY-MM-DD string.

    Supports strings and date/datetime-like values.
    """

    if value is None:
        return None

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    value = str(value).strip()

    if not value:
        return None

    return value[:10]


def _filter_trains_by_date(
    trains: list[dict],
    planning_date: str,
) -> list[dict]:
    """
    Keep only train movements belonging to planning_date.
    """

    target_date = _normalize_date(planning_date)

    return [
        train
        for train in trains
        if _normalize_date(train.get("date")) == target_date
    ]


def _filter_existing_blocks_by_date(
    existing_blocks: list[dict],
    planning_date: str,
) -> list[dict]:
    """
    Keep only existing blocks belonging to planning_date.
    """

    target_date = _normalize_date(planning_date)

    return [
        block
        for block in existing_blocks
        if _normalize_date(
            block.get("block_date")
        ) == target_date
    ]


def _filter_maintenance_tasks_by_date(
    maintenance_tasks: list[dict],
    planning_date: str,
) -> list[dict]:
    """
    Select maintenance tasks that are eligible for the
    requested planning date.

    A task is eligible when:

    1. Its preferred date is the planning date, OR
    2. Its due date has arrived/passed and the task is overdue.

    Tasks with a preferred date after the planning date are
    not scheduled early.
    """

    target_date = _normalize_date(planning_date)

    eligible_tasks = []

    for task in maintenance_tasks:

        preferred_date = _normalize_date(
            task.get("preferred_date")
        )

        due_date = _normalize_date(
            task.get("due_date")
        )

        overdue = task.get("overdue")

        # -----------------------------------------------------
        # Preferred date matches planning date
        # -----------------------------------------------------

        if preferred_date == target_date:
            eligible_tasks.append(task)
            continue

        # -----------------------------------------------------
        # Overdue maintenance can be considered
        # -----------------------------------------------------

        if overdue is True:
            eligible_tasks.append(task)
            continue

        # -----------------------------------------------------
        # Due date has arrived
        # -----------------------------------------------------

        if due_date is not None and due_date <= target_date:
            eligible_tasks.append(task)
            continue

    return eligible_tasks


def generate_block_plan(
    maintenance_tasks: list[dict],
    trains: list[dict],
    existing_blocks: list[dict] | None = None,
    planning_date: str | None = None,
) -> dict:
    """
    Generate a complete maintenance block recommendation.

    Flow:

        Raw maintenance requests
                ↓
        Date filtering
                ↓
        Train movements
                ↓
        Existing block filtering
                ↓
        Priority calculation
                ↓
        Coordination
                ↓
        Conflict checking
                ↓
        Available slot selection
                ↓
        BDMS recommendation

    If planning_date is not supplied, the function preserves
    the original behavior and uses the supplied records directly.
    """

    if existing_blocks is None:
        existing_blocks = []

    # ---------------------------------------------------------
    # 1. Preserve original behavior when no date is supplied
    # ---------------------------------------------------------

    if planning_date is None:

        filtered_tasks = maintenance_tasks
        filtered_trains = trains
        filtered_blocks = existing_blocks

    else:

        # -----------------------------------------------------
        # 2. Filter all data for planning date
        # -----------------------------------------------------

        filtered_tasks = _filter_maintenance_tasks_by_date(
            maintenance_tasks,
            planning_date,
        )

        filtered_trains = _filter_trains_by_date(
            trains,
            planning_date,
        )

        filtered_blocks = _filter_existing_blocks_by_date(
            existing_blocks,
            planning_date,
        )

    # ---------------------------------------------------------
    # 3. Optimize maintenance
    # ---------------------------------------------------------

    optimization_result = optimize_maintenance(
        maintenance_tasks=filtered_tasks,
        trains=filtered_trains,
        existing_blocks=filtered_blocks,
    )

    # ---------------------------------------------------------
    # 4. Build recommendation
    # ---------------------------------------------------------

    recommendation = build_recommendation(
        optimization_result["assignments"]
    )

    # ---------------------------------------------------------
    # 5. Return complete result
    # ---------------------------------------------------------

    result = {
        "optimization": optimization_result,
        "recommendation": recommendation,
    }

    if planning_date is not None:

        result["planning_date"] = _normalize_date(
            planning_date
        )

        result["input_summary"] = {
            "maintenance_tasks": len(filtered_tasks),
            "trains": len(filtered_trains),
            "existing_blocks": len(filtered_blocks),
        }

    return result