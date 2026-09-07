from backend.optimization.coordination import (
    can_coordinate,
    group_coordinated_tasks,
)


def test_different_departments_same_section_can_coordinate():

    tms_task = {
        "request_id": "TMS-001",
        "department": "ENGINEERING",
        "section_id": "SEC01",
    }

    smms_task = {
        "request_id": "SMMS-001",
        "department": "SIGNALLING",
        "section_id": "SEC01",
    }

    assert can_coordinate(
        tms_task,
        smms_task,
    ) is True


def test_different_sections_cannot_coordinate():

    tms_task = {
        "request_id": "TMS-001",
        "department": "ENGINEERING",
        "section_id": "SEC01",
    }

    smms_task = {
        "request_id": "SMMS-001",
        "department": "SIGNALLING",
        "section_id": "SEC02",
    }

    assert can_coordinate(
        tms_task,
        smms_task,
    ) is False


def test_same_department_cannot_coordinate():

    task_a = {
        "request_id": "TMS-001",
        "department": "ENGINEERING",
        "section_id": "SEC01",
    }

    task_b = {
        "request_id": "TMS-002",
        "department": "ENGINEERING",
        "section_id": "SEC01",
    }

    assert can_coordinate(
        task_a,
        task_b,
    ) is False


def test_tasks_are_grouped_by_section_and_department():

    tasks = [
        {
            "request_id": "TMS-001",
            "department": "ENGINEERING",
            "section_id": "SEC01",
        },
        {
            "request_id": "SMMS-001",
            "department": "SIGNALLING",
            "section_id": "SEC01",
        },
        {
            "request_id": "TDMS-001",
            "department": "TRACTION",
            "section_id": "SEC01",
        },
        {
            "request_id": "SMMS-002",
            "department": "SIGNALLING",
            "section_id": "SEC02",
        },
    ]

    groups = group_coordinated_tasks(tasks)

    assert len(groups) == 2

    sec01_group = next(
        group
        for group in groups
        if group[0]["section_id"] == "SEC01"
    )

    assert len(sec01_group) == 3