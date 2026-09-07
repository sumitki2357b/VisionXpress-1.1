from backend.services.slot_engine import find_available_slots


def test_find_available_slot_between_trains():

    trains = [
        {
            "train_id": "T001",
            "section_id": "SEC01",
            "start_time": "02:00",
            "end_time": "03:00",
        },
        {
            "train_id": "T002",
            "section_id": "SEC01",
            "start_time": "06:30",
            "end_time": "07:30",
        },
    ]

    slots = find_available_slots(
        maintenance_section="SEC01",
        duration_minutes=120,
        trains=trains,
    )

    assert {
        "start_time": "03:00",
        "end_time": "06:30",
        "duration_minutes": 210,
    } in slots


def test_short_gap_is_not_returned():

    trains = [
        {
            "train_id": "T001",
            "section_id": "SEC01",
            "start_time": "02:00",
            "end_time": "03:00",
        },
        {
            "train_id": "T002",
            "section_id": "SEC01",
            "start_time": "04:00",
            "end_time": "05:00",
        },
    ]

    slots = find_available_slots(
        maintenance_section="SEC01",
        duration_minutes=120,
        trains=trains,
    )

    # 03:00-04:00 is only 60 minutes
    assert {
        "start_time": "03:00",
        "end_time": "04:00",
        "duration_minutes": 60,
    } not in slots


def test_different_section_does_not_block():

    trains = [
        {
            "train_id": "T001",
            "section_id": "SEC02",
            "start_time": "01:00",
            "end_time": "05:00",
        }
    ]

    slots = find_available_slots(
        maintenance_section="SEC01",
        duration_minutes=120,
        trains=trains,
    )

    assert len(slots) == 1
    assert slots[0]["start_time"] == "00:00"


def test_no_trains_gives_full_day_slot():

    slots = find_available_slots(
        maintenance_section="SEC01",
        duration_minutes=120,
        trains=[],
    )

    assert len(slots) == 1
    assert slots[0]["start_time"] == "00:00"
    assert slots[0]["duration_minutes"] == 1439


def test_exact_duration_slot():

    trains = [
        {
            "train_id": "T001",
            "section_id": "SEC01",
            "start_time": "02:00",
            "end_time": "04:00",
        }
    ]

    slots = find_available_slots(
        maintenance_section="SEC01",
        duration_minutes=120,
        trains=trains,
        day_start="00:00",
        day_end="06:00",
    )

    assert {
        "start_time": "04:00",
        "end_time": "06:00",
        "duration_minutes": 120,
    } in slots