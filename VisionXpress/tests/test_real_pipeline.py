from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_maintenance_tasks,
    normalize_trains,
    normalize_existing_blocks,
    normalize_section_master,
)
from backend.services.planning_engine import generate_block_plan


def test_real_excel_pipeline():

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

    # ---------------------------------------------------------
    # Verify real Excel data was loaded
    # ---------------------------------------------------------

    assert len(tasks) > 0
    assert len(trains) > 0
    assert len(blocks) > 0
    assert len(sections) > 0

    # ---------------------------------------------------------
    # Generate maintenance plan for the planning date
    # ---------------------------------------------------------

    result = generate_block_plan(
        maintenance_tasks=tasks,
        trains=trains,
        existing_blocks=blocks,
        planning_date="2026-08-30",
    )

    # ---------------------------------------------------------
    # Verify complete pipeline output
    # ---------------------------------------------------------

    assert "planning_date" in result
    assert result["planning_date"] == "2026-08-30"

    assert "optimization" in result
    assert "recommendation" in result

    assert "assignments" in result["optimization"]
    assert "unscheduled" in result["optimization"]