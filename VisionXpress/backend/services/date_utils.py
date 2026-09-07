from datetime import date, datetime


def _normalize_date(value) -> str | None:
    """
    Convert common Excel/Python date values into YYYY-MM-DD.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    value = str(value).strip()

    if not value:
        return None

    # Handle values such as:
    # 2026-08-30 00:00:00
    if " " in value:
        value = value.split(" ")[0]

    return value


def filter_by_date(
    records: list[dict],
    date_field: str,
    planning_date: str,
) -> list[dict]:
    """
    Return only records belonging to the planning date.

    Supports:
    - YYYY-MM-DD strings
    - Python date objects
    - Python datetime objects
    - Excel-loaded datetime values
    """

    normalized_planning_date = _normalize_date(
        planning_date
    )

    filtered = []

    for record in records:

        record_date = _normalize_date(
            record.get(date_field)
        )

        if record_date == normalized_planning_date:
            filtered.append(record)

    return filtered