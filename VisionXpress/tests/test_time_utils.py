import pytest

from backend.services.time_utils import (
    time_to_minutes,
    minutes_to_time,
)


def test_time_to_minutes():
    assert time_to_minutes("00:00") == 0
    assert time_to_minutes("01:00") == 60
    assert time_to_minutes("04:00") == 240
    assert time_to_minutes("12:30") == 750
    assert time_to_minutes("23:59") == 1439


def test_minutes_to_time():
    assert minutes_to_time(0) == "00:00"
    assert minutes_to_time(60) == "01:00"
    assert minutes_to_time(240) == "04:00"
    assert minutes_to_time(750) == "12:30"
    assert minutes_to_time(1439) == "23:59"


def test_invalid_time_format():
    with pytest.raises(ValueError):
        time_to_minutes("1 PM")

    with pytest.raises(ValueError):
        time_to_minutes("0100")

    with pytest.raises(ValueError):
        time_to_minutes("abc")


def test_invalid_hour():
    with pytest.raises(ValueError):
        time_to_minutes("24:00")


def test_invalid_minute():
    with pytest.raises(ValueError):
        time_to_minutes("01:60")


def test_invalid_minutes_value():
    with pytest.raises(ValueError):
        minutes_to_time(-1)

    with pytest.raises(ValueError):
        minutes_to_time(1440)