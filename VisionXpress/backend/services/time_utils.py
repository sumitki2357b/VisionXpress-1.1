def time_to_minutes(time_str: str) -> int:
    """
    Convert a 24-hour HH:MM time into minutes from midnight.

    Example:
        "01:30" -> 90
        "04:00" -> 240
    """

    try:
        hours, minutes = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        raise ValueError("Time must be in HH:MM format")

    if hours < 0 or hours > 23:
        raise ValueError("Hour must be between 00 and 23")

    if minutes < 0 or minutes > 59:
        raise ValueError("Minute must be between 00 and 59")

    return hours * 60 + minutes


def minutes_to_time(total_minutes: int) -> str:
    """
    Convert minutes from midnight into 24-hour HH:MM format.

    Example:
        90 -> "01:30"
        240 -> "04:00"
    """

    if not isinstance(total_minutes, int):
        raise ValueError("Minutes must be an integer")

    if total_minutes < 0 or total_minutes > 1439:
        raise ValueError("Minutes must be between 0 and 1439")

    hours = total_minutes // 60
    minutes = total_minutes % 60

    return f"{hours:02d}:{minutes:02d}"