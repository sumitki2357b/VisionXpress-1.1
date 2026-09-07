REQUIRED_MAINTENANCE_FIELDS = {
    "request_id",
    "department",
    "source_system",
    "section_id",
    "asset_id",
    "asset_type",
    "work_description",
    "maintenance_category",
    "defect_severity",
    "failure_risk",
    "safety_related",
    "asset_operational_status",
    "estimated_duration_minutes",
    "requires_block",
    "block_type_required",
}


REQUIRED_COA_FIELDS = {
    "train_id",
    "section_id",
    "start_time",
    "end_time",
}


def validate_required_fields(
    record: dict,
    required_fields: set[str],
) -> list[str]:
    """
    Return a list of missing required fields.
    """

    missing = []

    for field in required_fields:

        if field not in record:
            missing.append(field)
            continue

        value = record[field]

        if value is None:
            missing.append(field)
            continue

        if isinstance(value, str) and not value.strip():
            missing.append(field)

    return missing


def validate_maintenance_task(
    task: dict,
) -> tuple[bool, list[str]]:
    """
    Validate one maintenance request.
    """

    errors = validate_required_fields(
        task,
        REQUIRED_MAINTENANCE_FIELDS,
    )

    duration = task.get(
        "estimated_duration_minutes"
    )

    if duration is not None:

        try:
            duration = int(duration)

            if duration <= 0:
                errors.append(
                    "estimated_duration_minutes must be greater than 0"
                )

        except (TypeError, ValueError):

            errors.append(
                "estimated_duration_minutes must be an integer"
            )

    return len(errors) == 0, errors


def validate_coa_train(
    train: dict,
) -> tuple[bool, list[str]]:
    """
    Validate one COA train record.
    """

    errors = validate_required_fields(
        train,
        REQUIRED_COA_FIELDS,
    )

    start_time = train.get("start_time")
    end_time = train.get("end_time")

    if start_time is not None:
        if not _valid_time_format(start_time):
            errors.append(
                "start_time must use HH:MM 24-hour format"
            )

    if end_time is not None:
        if not _valid_time_format(end_time):
            errors.append(
                "end_time must use HH:MM 24-hour format"
            )

    return len(errors) == 0, errors


def validate_maintenance_tasks(
    tasks: list[dict],
) -> dict:
    """
    Validate all maintenance requests.
    """

    valid_tasks = []
    invalid_tasks = []

    for task in tasks:

        valid, errors = validate_maintenance_task(
            task
        )

        if valid:
            valid_tasks.append(task)

        else:
            invalid_tasks.append(
                {
                    "record": task,
                    "errors": errors,
                }
            )

    return {
        "valid": len(invalid_tasks) == 0,
        "valid_tasks": valid_tasks,
        "invalid_tasks": invalid_tasks,
        "total": len(tasks),
        "valid_count": len(valid_tasks),
        "invalid_count": len(invalid_tasks),
    }


def validate_coa_trains(
    trains: list[dict],
) -> dict:
    """
    Validate all COA train records.
    """

    valid_trains = []
    invalid_trains = []

    for train in trains:

        valid, errors = validate_coa_train(
            train
        )

        if valid:
            valid_trains.append(train)

        else:
            invalid_trains.append(
                {
                    "record": train,
                    "errors": errors,
                }
            )

    return {
        "valid": len(invalid_trains) == 0,
        "valid_trains": valid_trains,
        "invalid_trains": invalid_trains,
        "total": len(trains),
        "valid_count": len(valid_trains),
        "invalid_count": len(invalid_trains),
    }


def _valid_time_format(value) -> bool:
    """
    Check HH:MM 24-hour time format.
    """

    if not isinstance(value, str):
        return False

    parts = value.split(":")

    if len(parts) != 2:
        return False

    try:
        hour = int(parts[0])
        minute = int(parts[1])

    except ValueError:
        return False

    return (
        0 <= hour <= 23
        and
        0 <= minute <= 59
    )