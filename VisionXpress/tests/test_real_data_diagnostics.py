from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_maintenance_tasks,
    normalize_trains,
    normalize_existing_blocks,
)
from backend.services.date_utils import filter_by_date


def test_real_data_diagnostics():

    planning_date = "2026-09-01"

    # ---------------------------------------------------------
    # 1. Load data
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 2. Basic counts
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("VISIONXPRESS DATA DIAGNOSTICS")
    print("=" * 70)

    print(f"Maintenance tasks : {len(tasks)}")
    print(f"Trains            : {len(trains)}")
    print(f"Existing blocks   : {len(blocks)}")

    # ---------------------------------------------------------
    # 3. Inspect train dates
    # ---------------------------------------------------------

    print("\n")
    print("TRAIN DATE VALUES")
    print("-" * 70)

    train_dates = {}

    for train in trains:

        value = train.get("date")

        value_type = type(value).__name__

        key = (str(value), value_type)

        train_dates[key] = train_dates.get(key, 0) + 1

    for (date_value, value_type), count in train_dates.items():

        print(
            f"{date_value!r:30} "
            f"type={value_type:15} "
            f"count={count}"
        )

    # ---------------------------------------------------------
    # 4. Inspect block dates
    # ---------------------------------------------------------

    print("\n")
    print("EXISTING BLOCK DATES")
    print("-" * 70)

    block_dates = {}

    for block in blocks:

        value = block.get("block_date")

        value_type = type(value).__name__

        key = (str(value), value_type)

        block_dates[key] = block_dates.get(key, 0) + 1

    for (date_value, value_type), count in block_dates.items():

        print(
            f"{date_value!r:30} "
            f"type={value_type:15} "
            f"count={count}"
        )

    # ---------------------------------------------------------
    # 5. Apply current date filtering
    # ---------------------------------------------------------

    planning_trains = filter_by_date(
        records=trains,
        date_field="date",
        planning_date=planning_date,
    )

    planning_blocks = filter_by_date(
        records=blocks,
        date_field="block_date",
        planning_date=planning_date,
    )

    # ---------------------------------------------------------
    # 6. Show filtering result
    # ---------------------------------------------------------

    print("\n")
    print("DATE FILTER RESULT")
    print("-" * 70)

    print(f"Planning date      : {planning_date}")
    print(f"Filtered trains    : {len(planning_trains)}")
    print(f"Filtered blocks    : {len(planning_blocks)}")

    # ---------------------------------------------------------
    # 7. Show sample trains
    # ---------------------------------------------------------

    print("\n")
    print("SAMPLE FILTERED TRAINS")
    print("-" * 70)

    for train in planning_trains[:10]:

        print(
            f"{train.get('train_id'):15} "
            f"{train.get('section_id'):10} "
            f"{train.get('start_time')} -> "
            f"{train.get('end_time')} "
            f"| date={train.get('date')!r}"
        )

    # ---------------------------------------------------------
    # 8. Show sample blocks
    # ---------------------------------------------------------

    print("\n")
    print("FILTERED EXISTING BLOCKS")
    print("-" * 70)

    for block in planning_blocks:

        print(
            f"{block.get('block_calendar_id'):15} "
            f"{block.get('section_id'):10} "
            f"{block.get('start_time')} -> "
            f"{block.get('end_time')} "
            f"| department={block.get('approved_for_department')} "
            f"| status={block.get('block_status')} "
            f"| date={block.get('block_date')!r}"
        )

    # ---------------------------------------------------------
    # 9. Don't make assumptions about expected counts yet.
    # ---------------------------------------------------------

    assert len(trains) > 0
    assert len(blocks) > 0

        # ---------------------------------------------------------
    # 10. Maintenance preferred-date analysis
    # ---------------------------------------------------------

    print("\n")
    print("MAINTENANCE PREFERRED DATES")
    print("-" * 70)

    preferred_dates = {}

    for task in tasks:

        value = task.get("preferred_date")

        key = str(value) if value not in (None, "") else "<BLANK>"

        preferred_dates[key] = (
            preferred_dates.get(key, 0) + 1
        )

    for date_value, count in sorted(preferred_dates.items()):

        print(
            f"{date_value:30} "
            f"count={count}"
        )

    # ---------------------------------------------------------
    # 11. Maintenance due-date analysis
    # ---------------------------------------------------------

    print("\n")
    print("MAINTENANCE DUE DATES")
    print("-" * 70)

    due_dates = {}

    for task in tasks:

        value = task.get("due_date")

        key = str(value) if value not in (None, "") else "<BLANK>"

        due_dates[key] = (
            due_dates.get(key, 0) + 1
        )

    for date_value, count in sorted(due_dates.items()):

        print(
            f"{date_value:30} "
            f"count={count}"
        )