from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_maintenance_tasks,
    normalize_trains,
    normalize_existing_blocks,
    normalize_section_master,
)


def test_normalize_real_data():

    data = load_all_data()

    tasks = normalize_maintenance_tasks(
        data["tms"],
        data["tdms"],
        data["smms"],
    )

    trains = normalize_trains(
        data["coa"]
    )

    blocks = normalize_existing_blocks(
        data["existing_blocks"]
    )

    sections = normalize_section_master(
        data["section_master"]
    )

    assert len(tasks) > 0
    assert len(trains) > 0
    assert len(blocks) > 0
    assert len(sections) > 0

    assert "request_id" in tasks[0]
    assert "section_id" in tasks[0]

    assert "train_id" in trains[0]
    assert "start_time" in trains[0]
    assert "end_time" in trains[0]

    assert "block_calendar_id" in blocks[0]
    assert "section_id" in blocks[0]

    assert "section_id" in sections[0]