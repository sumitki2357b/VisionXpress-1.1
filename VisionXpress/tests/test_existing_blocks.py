from backend.services.slot_engine import find_available_slots


def test_maintenance_uses_existing_block():

    trains = [
        {
            "train_id": "TRAIN-001",
            "section_id": "SEC01",
            "start_time": "00:00",
            "end_time": "05:00",
        }
    ]

    existing_blocks = [
        {
            "block_calendar_id": "BLOCK-001",
            "section_id": "SEC01",
            "block_date": "2026-08-30",
            "start_time": "05:00",
            "end_time": "07:00",
            "approved_for_department": "ENGINEERING",
            "block_status": "AVAILABLE",
        }
    ]

    slots = find_available_slots(
        maintenance_section="SEC01",
        duration_minutes=120,
        trains=trains,
        existing_blocks=existing_blocks,
    )

    assert len(slots) == 1

    assert slots[0]["start_time"] == "05:00"
    assert slots[0]["end_time"] == "07:00"
    assert slots[0]["duration_minutes"] == 120