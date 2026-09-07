def can_coordinate(task_a: dict, task_b: dict) -> bool:
    """
    Determine whether two maintenance tasks can be
    performed during the same maintenance block.
    """

    # They must belong to the same section.
    if task_a["section_id"] != task_b["section_id"]:
        return False

    # They must not belong to the same department.
    if task_a["department"] == task_b["department"]:
        return False

    # For the prototype, assume tasks can share a block.
    return True


def group_coordinated_tasks(tasks: list[dict]) -> list[list[dict]]:
    """
    Group maintenance tasks that can potentially
    share a maintenance block.
    """

    groups = []

    for task in tasks:

        added_to_group = False

        for group in groups:

            if all(
                can_coordinate(task, existing_task)
                for existing_task in group
            ):
                group.append(task)
                added_to_group = True
                break

        if not added_to_group:
            groups.append([task])

    return groups