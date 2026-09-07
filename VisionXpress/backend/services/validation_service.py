from __future__ import annotations

from datetime import datetime


ALLOWED_DEPARTMENTS = {"TMS", "TDMS", "SMMS", "COA", "BDMS"}
ALLOWED_SEVERITY = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
ALLOWED_RISK = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
ALLOWED_ASSET_STATUS = {"FAILED", "RESTRICTED", "DEGRADED", "OPERATIONAL", "NORMAL"}
ALLOWED_BLOCK_TYPES = {"PARTIAL", "FULL"}


def validate_maintenance_business_rules(task: dict, known_sections: set[str]) -> list[str]:
    errors: list[str] = []

    section = str(task.get("section_id") or "").strip()
    if section and section not in known_sections:
        errors.append(f"Unknown section_id: {section}")

    severity = str(task.get("defect_severity") or "").strip().upper()
    if severity and severity not in ALLOWED_SEVERITY:
        errors.append("defect_severity must be CRITICAL, HIGH, MEDIUM or LOW")

    risk = str(task.get("failure_risk") or "").strip().upper()
    if risk and risk not in ALLOWED_RISK:
        errors.append("failure_risk must be CRITICAL, HIGH, MEDIUM or LOW")

    status = str(task.get("asset_operational_status") or "").strip().upper()
    if status and status not in ALLOWED_ASSET_STATUS:
        errors.append("asset_operational_status contains an unsupported value")

    block_type = str(task.get("block_type_required") or "").strip().upper()
    if block_type and block_type not in ALLOWED_BLOCK_TYPES:
        errors.append("block_type_required must be PARTIAL or FULL")

    quantity = task.get("affected_asset_quantity")
    if quantity is not None:
        try:
            if int(quantity) < 1:
                errors.append("affected_asset_quantity must be at least 1")
        except (TypeError, ValueError):
            errors.append("affected_asset_quantity must be an integer")

    duration = task.get("estimated_duration_minutes")
    try:
        if duration is None or int(duration) <= 0:
            errors.append("estimated_duration_minutes must be greater than 0")
    except (TypeError, ValueError):
        errors.append("estimated_duration_minutes must be an integer")

    for field in ["due_date", "preferred_date", "last_maintenance_date"]:
        value = task.get(field)
        if value:
            try:
                datetime.strptime(str(value)[:10], "%Y-%m-%d")
            except ValueError:
                errors.append(f"{field} must use YYYY-MM-DD format")

    for field in ["preferred_start_time", "preferred_end_time"]:
        value = task.get(field)
        if value and not _valid_time(value):
            errors.append(f"{field} must use HH:MM 24-hour format")

    start = task.get("preferred_start_time")
    end = task.get("preferred_end_time")
    if start and end and _valid_time(start) and _valid_time(end):
        if _minutes(start) >= _minutes(end):
            errors.append("preferred_end_time must be later than preferred_start_time")

    return errors


def validate_coa_business_rules(train: dict, known_sections: set[str]) -> list[str]:
    errors: list[str] = []
    section = str(train.get("section_id") or "").strip()
    if section and section not in known_sections:
        errors.append(f"Unknown Section_ID: {section}")
    value = train.get("date")
    if value:
        try:
            datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            errors.append("date must use YYYY-MM-DD format")
    for field in ["start_time", "end_time"]:
        if not _valid_time(train.get(field)):
            errors.append(f"{field} must use HH:MM 24-hour format")
    if _valid_time(train.get("start_time")) and _valid_time(train.get("end_time")):
        if _minutes(train["start_time"]) >= _minutes(train["end_time"]):
            errors.append("end_time must be later than start_time")
    return errors


def _valid_time(value) -> bool:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return False
    try:
        hour, minute = map(int, value.split(":"))
    except ValueError:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute
