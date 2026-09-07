from backend.services.time_utils import (
    time_to_minutes,
    minutes_to_time,
)


def find_available_slots(
    maintenance_section: str,
    duration_minutes: int,
    trains: list[dict],
    existing_blocks: list[dict] | None = None,
    day_start: str = "00:00",
    day_end: str = "23:59",
) -> list[dict]:
    """
    Find available maintenance windows for a section.

    Existing approved/available blocks are preferred when they
    provide a feasible maintenance window.

    If no existing block is available, the function searches
    the complete planning day for free windows between train
    movements.

    Each returned slot represents the COMPLETE free window
    between train movements, unless it is an existing block.

    The optimizer can later select the exact maintenance
    duration inside the returned window.
    """

    start_of_day = time_to_minutes(day_start)
    end_of_day = time_to_minutes(day_end)

    if existing_blocks is None:
        existing_blocks = []

    # ---------------------------------------------------------
    # 1. Determine planning windows from existing blocks
    # ---------------------------------------------------------

    planning_windows = []

    if existing_blocks:

        for block in existing_blocks:

            if block["section_id"] != maintenance_section:
                continue

            # Only available blocks can be reused
            if block.get("block_status") not in {"AVAILABLE", "APPROVED"}:
                continue

            block_start = time_to_minutes(
                block["start_time"]
            )

            block_end = time_to_minutes(
                block["end_time"]
            )

            # Ignore blocks outside planning window
            if block_end <= start_of_day:
                continue

            if block_start >= end_of_day:
                continue

            block_start = max(
                block_start,
                start_of_day,
            )

            block_end = min(
                block_end,
                end_of_day,
            )

            if block_start < block_end:

                planning_windows.append(
                    (
                        block_start,
                        block_end,
                    )
                )

    else:

        # No existing block data means use the
        # complete planning day.
        planning_windows.append(
            (
                start_of_day,
                end_of_day,
            )
        )

    # ---------------------------------------------------------
    # 2. Collect train intervals for this section
    # ---------------------------------------------------------

    blocked_intervals = []

    for train in trains:

        if train["section_id"] != maintenance_section:
            continue

        train_start = time_to_minutes(
            train["start_time"]
        )

        train_end = time_to_minutes(
            train["end_time"]
        )

        # Ignore trains outside planning window
        if train_end <= start_of_day:
            continue

        if train_start >= end_of_day:
            continue

        train_start = max(
            train_start,
            start_of_day,
        )

        train_end = min(
            train_end,
            end_of_day,
        )

        blocked_intervals.append(
            (
                train_start,
                train_end,
            )
        )

    # ---------------------------------------------------------
    # 3. Sort train intervals
    # ---------------------------------------------------------

    blocked_intervals.sort()

    # ---------------------------------------------------------
    # 4. Merge overlapping train intervals
    # ---------------------------------------------------------

    merged_intervals = []

    for interval_start, interval_end in blocked_intervals:

        if not merged_intervals:

            merged_intervals.append(
                [
                    interval_start,
                    interval_end,
                ]
            )

            continue

        previous_start, previous_end = (
            merged_intervals[-1]
        )

        if interval_start <= previous_end:

            merged_intervals[-1][1] = max(
                previous_end,
                interval_end,
            )

        else:

            merged_intervals.append(
                [
                    interval_start,
                    interval_end,
                ]
            )

    # ---------------------------------------------------------
    # 5. Prefer existing available blocks
    # ---------------------------------------------------------

    existing_block_slots = []

    for block in existing_blocks:

        if block["section_id"] != maintenance_section:
            continue

        if block.get("block_status") not in {"AVAILABLE", "APPROVED"}:
            continue

        block_start = time_to_minutes(
            block["start_time"]
        )

        block_end = time_to_minutes(
            block["end_time"]
        )

        # Ignore blocks outside planning window
        if block_end <= start_of_day:
            continue

        if block_start >= end_of_day:
            continue

        block_start = max(
            block_start,
            start_of_day,
        )

        block_end = min(
            block_end,
            end_of_day,
        )

        block_duration = (
            block_end - block_start
        )

        # Block must be large enough
        if block_duration < duration_minutes:
            continue

        # Check whether any train overlaps
        # the existing maintenance block.
        has_train_conflict = any(
            train_start < block_end
            and train_end > block_start
            for train_start, train_end in merged_intervals
        )

        if has_train_conflict:
            continue

        existing_block_slots.append(
            {
                "start_time": minutes_to_time(
                    block_start
                ),
                "end_time": minutes_to_time(
                    block_end
                ),
                "duration_minutes": block_duration,
                "existing_block": True,
                "block_calendar_id": block.get(
                    "block_calendar_id"
                ),
            }
        )

    # ---------------------------------------------------------
    # 6. If an existing block is feasible, use it
    # ---------------------------------------------------------

    if existing_block_slots:

        existing_block_slots.sort(
            key=lambda slot: time_to_minutes(
                slot["start_time"]
            )
        )

        return existing_block_slots

    # ---------------------------------------------------------
    # 7. Find COMPLETE free windows
    # ---------------------------------------------------------

    available_slots = []

    # If existing blocks were supplied but none were usable,
    # do NOT automatically treat the entire day as available.
    #
    # The existing block calendar represents the planned
    # maintenance windows for this section.
    if existing_blocks:

        for window_start, window_end in planning_windows:

            current_time = window_start

            for blocked_start, blocked_end in merged_intervals:

                # Train does not affect this planning window
                if blocked_end <= window_start:
                    continue

                if blocked_start >= window_end:
                    break

                effective_blocked_start = max(
                    blocked_start,
                    window_start,
                )

                effective_blocked_end = min(
                    blocked_end,
                    window_end,
                )

                if current_time < effective_blocked_start:

                    gap_duration = (
                        effective_blocked_start
                        - current_time
                    )

                    if gap_duration >= duration_minutes:

                        available_slots.append(
                            {
                                "start_time": minutes_to_time(
                                    current_time
                                ),
                                "end_time": minutes_to_time(
                                    effective_blocked_start
                                ),
                                "duration_minutes": gap_duration,
                            }
                        )

                current_time = max(
                    current_time,
                    effective_blocked_end,
                )

            # Remaining part of planning window
            if current_time < window_end:

                gap_duration = (
                    window_end - current_time
                )

                if gap_duration >= duration_minutes:

                    available_slots.append(
                        {
                            "start_time": minutes_to_time(
                                current_time
                            ),
                            "end_time": minutes_to_time(
                                window_end
                            ),
                            "duration_minutes": gap_duration,
                        }
                    )

        return available_slots

    # ---------------------------------------------------------
    # 8. Original behavior when no existing blocks exist
    # ---------------------------------------------------------

    current_time = start_of_day

    for blocked_start, blocked_end in merged_intervals:

        if current_time < blocked_start:

            gap_duration = (
                blocked_start - current_time
            )

            if gap_duration >= duration_minutes:

                available_slots.append(
                    {
                        "start_time": minutes_to_time(
                            current_time
                        ),
                        "end_time": minutes_to_time(
                            blocked_start
                        ),
                        "duration_minutes": gap_duration,
                    }
                )

        current_time = max(
            current_time,
            blocked_end,
        )

    # ---------------------------------------------------------
    # 9. Free window after final train
    # ---------------------------------------------------------

    if current_time < end_of_day:

        gap_duration = (
            end_of_day - current_time
        )

        if gap_duration >= duration_minutes:

            available_slots.append(
                {
                    "start_time": minutes_to_time(
                        current_time
                    ),
                    "end_time": minutes_to_time(
                        end_of_day
                    ),
                    "duration_minutes": gap_duration,
                }
            )

    # ---------------------------------------------------------
    # 10. No trains = entire planning window available
    # ---------------------------------------------------------

    if not merged_intervals:

        full_day_duration = (
            end_of_day - start_of_day
        )

        if full_day_duration >= duration_minutes:

            return [
                {
                    "start_time": minutes_to_time(
                        start_of_day
                    ),
                    "end_time": minutes_to_time(
                        end_of_day
                    ),
                    "duration_minutes": full_day_duration,
                }
            ]

    return available_slots