from backend.services.time_utils import time_to_minutes


def check_time_overlap(
    start_a: str,
    end_a: str,
    start_b: str,
    end_b: str,
) -> bool:
    """
    Check whether two time intervals overlap.

    Returns:
        True  -> intervals overlap
        False -> intervals do not overlap
    """

    start_a_minutes = time_to_minutes(start_a)
    end_a_minutes = time_to_minutes(end_a)

    start_b_minutes = time_to_minutes(start_b)
    end_b_minutes = time_to_minutes(end_b)

    return (
        start_a_minutes < end_b_minutes
        and start_b_minutes < end_a_minutes
    )


def check_section_compatibility(
    maintenance_section: str,
    train_section: str,
) -> bool:
    """
    Maintenance and train must belong to the same section
    for the train to create a direct block conflict.
    """

    return maintenance_section == train_section


def check_train_conflict(
    maintenance_section: str,
    maintenance_start: str,
    maintenance_end: str,
    train_section: str,
    train_start: str,
    train_end: str,
) -> tuple[bool, str]:
    """
    Determine whether a train conflicts with maintenance.

    Returns:
        (True, reason)  -> conflict exists
        (False, reason) -> no conflict
    """

    if not check_section_compatibility(
        maintenance_section,
        train_section,
    ):
        return False, "Different sections"

    if check_time_overlap(
        maintenance_start,
        maintenance_end,
        train_start,
        train_end,
    ):
        return True, "Train overlaps maintenance window"

    return False, "No time overlap"