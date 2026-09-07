from backend.services.date_utils import filter_by_date


def test_filter_by_date():

    records = [
        {
            "date": "2026-08-30",
            "id": "A",
        },
        {
            "date": "2026-08-31",
            "id": "B",
        },
        {
            "date": "2026-08-30",
            "id": "C",
        },
    ]

    result = filter_by_date(
        records,
        date_field="date",
        planning_date="2026-08-30",
    )

    assert len(result) == 2

    assert result[0]["id"] == "A"
    assert result[1]["id"] == "C"