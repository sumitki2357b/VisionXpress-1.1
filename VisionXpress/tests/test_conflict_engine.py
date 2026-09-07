from backend.services.conflict_engine import (
    check_time_overlap,
    check_section_compatibility,
    check_train_conflict,
)


def test_overlapping_times():
    assert check_time_overlap(
        "01:00",
        "04:00",
        "02:00",
        "03:00",
    ) is True


def test_non_overlapping_times():
    assert check_time_overlap(
        "01:00",
        "04:00",
        "04:00",
        "05:00",
    ) is False


def test_partial_overlap():
    assert check_time_overlap(
        "01:00",
        "04:00",
        "03:00",
        "05:00",
    ) is True


def test_different_sections():
    assert check_section_compatibility(
        "SEC01",
        "SEC02",
    ) is False


def test_same_sections():
    assert check_section_compatibility(
        "SEC01",
        "SEC01",
    ) is True


def test_train_conflict():
    conflict, reason = check_train_conflict(
        maintenance_section="SEC01",
        maintenance_start="01:00",
        maintenance_end="04:00",
        train_section="SEC01",
        train_start="02:00",
        train_end="03:00",
    )

    assert conflict is True
    assert reason == "Train overlaps maintenance window"


def test_different_section_no_conflict():
    conflict, reason = check_train_conflict(
        maintenance_section="SEC01",
        maintenance_start="01:00",
        maintenance_end="04:00",
        train_section="SEC02",
        train_start="02:00",
        train_end="03:00",
    )

    assert conflict is False
    assert reason == "Different sections"


def test_train_after_maintenance():
    conflict, reason = check_train_conflict(
        maintenance_section="SEC01",
        maintenance_start="01:00",
        maintenance_end="04:00",
        train_section="SEC01",
        train_start="04:00",
        train_end="05:00",
    )

    assert conflict is False
    assert reason == "No time overlap"