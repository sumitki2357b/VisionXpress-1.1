from __future__ import annotations

import io
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from backend.config import DATA_DIR
from backend.database import (
    add_notification,
    audit,
    get_block,
    get_request,
    latest_coa_for_date,
    list_blocks,
    list_requests,
    save_block,
    save_request,
    update_block,
    update_request_status,
)
from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import (
    normalize_existing_blocks,
    normalize_maintenance_tasks,
    normalize_section_master,
    normalize_trains,
)
from backend.services.date_utils import filter_by_date
from backend.services.input_loader import load_file
from backend.services.input_validator import (
    REQUIRED_COA_FIELDS,
    REQUIRED_MAINTENANCE_FIELDS,
    validate_coa_train,
    validate_maintenance_task,
    validate_required_fields,
)
from backend.services.planning_engine import generate_block_plan
from backend.services.slot_engine import find_available_slots
from backend.services.time_utils import time_to_minutes, minutes_to_time
from backend.services.validation_service import (
    validate_maintenance_business_rules,
    validate_coa_business_rules,
)


MAINTENANCE_RAW_TO_CANONICAL = {
    "request_id": "Request_id",
    "requestid": "Request_id",
    "request id": "Request_id",
    "department": "Department",
    "source_system": "Source_system",
    "sourcesystem": "Source_system",
    "location": "Location",
    "section_id": "Section_id",
    "sectionid": "Section_id",
    "asset_id": "Asset_id",
    "assetid": "Asset_id",
    "asset_type": "Asset_type",
    "work_description": "Work_description",
    "maintenance_category": "Maintenance_category",
    "defect_id": "Defect_id",
    "defect_severity": "Defect_severity",
    "failure_risk": "Failure_risk",
    "safety_related": "Safety_related",
    "asset_operational_status": "Asset_operational_status",
    "affected_asset_quantity": "Affected_asset_quantity",
    "last_maintenance_date": "Last_maintenance_date",
    "due_date": "Due_date",
    "overdue": "Overdue",
    "estimated_duration_minutes": "Estimated_duration_minutes",
    "required_resources": "Required_resources",
    "requires_block": "Requires_block",
    "block_type_required": "Block_type_required",
    "preferred_date": "Preferred_date",
    "preferred_start_time": "Preferred_start_time",
    "preferred_end_time": "Preferred_end_time",
    "request_status": "Request_status",
}

COA_RAW_TO_CANONICAL = {
    "train_id": "Train_ID",
    "trainid": "Train_ID",
    "date": "Date",
    "train_type": "Train_Type",
    "route_id": "Route_ID",
    "section_id": "Section_ID",
    "start_station": "Start_Station",
    "end_station": "End_Station",
    "start_time": "Start_Time",
    "end_time": "End_Time",
    "direction": "Direction",
    "train_priority": "Train_Priority",
    "operational_status": "Operational_Status",
}


def _norm_header(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("-", "_").split())


def canonicalize_row(row: dict, mapping: dict[str, str]) -> dict:
    result = {}
    normalized = {_norm_header(k): v for k, v in row.items()}
    for key, value in normalized.items():
        canonical = mapping.get(key, key)
        result[canonical] = _clean_value(value)
    return result


def _clean_value(value: Any):
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in {"true", "yes", "y", "1"}:
            return True
        if value.lower() in {"false", "no", "n", "0"}:
            return False
        return value
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return value


def load_uploaded_rows(raw_bytes: bytes, filename: str) -> list[dict]:
    temp_dir = DATA_DIR / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / Path(filename).name
    temp_path.write_bytes(raw_bytes)
    try:
        return load_file(str(temp_path))
    finally:
        temp_path.unlink(missing_ok=True)


def maintenance_headers() -> list[str]:
    return [
        "Request_id", "Department", "Source_system", "Location", "Section_id",
        "Asset_id", "Asset_type", "Work_description", "Maintenance_category",
        "Defect_id", "Defect_severity", "Failure_risk", "Safety_related",
        "Asset_operational_status", "Affected_asset_quantity", "Last_maintenance_date",
        "Due_date", "Overdue", "Estimated_duration_minutes", "Required_resources",
        "Requires_block", "Block_type_required", "Preferred_date",
        "Preferred_start_time", "Preferred_end_time", "Request_status",
    ]


def coa_headers() -> list[str]:
    return [
        "Train_ID", "Train_Type", "Date", "Route_ID", "Section_ID",
        "Start_Station", "End_Station", "Start_Time", "End_Time", "Direction",
        "Train_Priority", "Operational_Status",
    ]


def validate_maintenance_upload(rows: list[dict], department: str, sections: list[dict]) -> dict:
    normalized = [canonicalize_row(row, MAINTENANCE_RAW_TO_CANONICAL) for row in rows]
    normalized_internal = normalize_maintenance_tasks(normalized, [], [])
    errors = []
    valid = []
    section_ids = {str(s.get("Section_id")).strip() for s in normalized if s.get("Section_id")}
    known_sections = {str(s.get("Section_id")).strip() for s in sections}
    seen_ids = set()

    for index, (raw, task) in enumerate(zip(normalized, normalized_internal), start=2):
        row_errors = validate_required_fields(raw, REQUIRED_MAINTENANCE_FIELDS)
        if raw.get("Department") and str(raw["Department"]).strip().upper() != department:
            row_errors.append(f"Department must match logged-in department: {department}")
        rid = raw.get("Request_id")
        if rid in seen_ids:
            row_errors.append("Duplicate Request_id in uploaded file")
        if rid:
            seen_ids.add(rid)
            if get_request(str(rid)):
                row_errors.append("Request_id already exists in VisionXpress")
        section_id = raw.get("Section_id")
        if section_id and str(section_id).strip() not in known_sections:
            row_errors.append(f"Unknown Section_id: {section_id}")
        ok, task_errors = validate_maintenance_task(task)
        row_errors.extend(task_errors)
        row_errors.extend(_validate_dates_and_times(task))
        row_errors.extend(
            validate_maintenance_business_rules(
                task,
                known_sections,
            )
        )
        if row_errors:
            errors.append({"row": index, "request_id": rid, "errors": sorted(set(row_errors))})
        else:
            valid.append(task)

    return {
        "valid": not errors,
        "accepted_count": len(valid),
        "total": len(rows),
        "invalid_count": len(errors),
        "errors": errors,
        "tasks": valid,
    }


def _validate_dates_and_times(task: dict) -> list[str]:
    errors = []
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
        if time_to_minutes(start) >= time_to_minutes(end):
            errors.append("preferred_end_time must be later than preferred_start_time")
    return errors


def validate_coa_upload(rows: list[dict], sections: list[dict]) -> dict:
    normalized = [canonicalize_row(row, COA_RAW_TO_CANONICAL) for row in rows]
    internal = normalize_trains(normalized)
    errors = []
    valid = []
    known_sections = {str(s.get("Section_id")).strip() for s in sections}
    seen = set()
    for index, (raw, train) in enumerate(zip(normalized, internal), start=2):
        row_errors = validate_required_fields(raw, REQUIRED_COA_FIELDS)
        ok, train_errors = validate_coa_train(train)
        row_errors.extend(train_errors)
        row_errors.extend(
            validate_coa_business_rules(
                train,
                known_sections,
            )
        )
        if train.get("date"):
            try:
                datetime.strptime(str(train["date"])[:10], "%Y-%m-%d")
            except ValueError:
                row_errors.append("date must use YYYY-MM-DD format")
        if train.get("section_id") and train["section_id"] not in known_sections:
            row_errors.append(f"Unknown Section_ID: {train['section_id']}")
        if train.get("train_id") in seen:
            row_errors.append("Duplicate Train_ID in uploaded file")
        if train.get("train_id"):
            seen.add(train["train_id"])
        if row_errors:
            errors.append({"row": index, "train_id": train.get("train_id"), "errors": sorted(set(row_errors))})
        else:
            valid.append(train)
    return {
        "valid": not errors,
        "accepted_count": len(valid),
        "total": len(rows),
        "invalid_count": len(errors),
        "errors": errors,
        "trains": valid,
    }


def _valid_time(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return False
    try:
        h, m = map(int, value.split(":"))
        return 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        return False


def next_task_id(department: str) -> str:
    prefix = department.upper()
    existing = [r["request_id"] for r in list_requests() if str(r["request_id"]).upper().startswith(prefix + "-")]
    numbers = []
    for rid in existing:
        try:
            numbers.append(int(str(rid).split("-")[-1]))
        except Exception:
            continue
    return f"{prefix}-{(max(numbers, default=0) + 1):03d}"


def create_manual_request(payload: dict, user: dict) -> dict:
    data = dict(payload)
    data["request_id"] = data.get("request_id") or next_task_id(user["department"])
    data["department"] = user["department"]
    data["source_system"] = user["department"]
    data["request_status"] = "SUBMITTED"
    ok, errors = validate_maintenance_task(data)
    sections = _section_lookup()
    errors.extend(_validate_dates_and_times(data))
    errors.extend(
        validate_maintenance_business_rules(
            data,
            set(sections.keys()),
        )
    )
    if not ok or errors:
        return {"valid": False, "errors": sorted(set(errors))}
    if get_request(data["request_id"]):
        return {"valid": False, "errors": ["request_id already exists"]}
    save_request(data, status="SUBMITTED")
    audit(user["user_id"], "SUBMIT_REQUEST", "maintenance_request", data["request_id"], {})
    return {"valid": True, "request": data}


def save_uploaded_maintenance(tasks: list[dict], user: dict) -> dict:
    if not tasks:
        return {"saved": 0, "requests": []}
    saved = []
    for task in tasks:
        task = normalize_maintenance_tasks([task], [], [])[0]
        task["department"] = user["department"]
        task["source_system"] = user["department"]
        task["request_status"] = "SUBMITTED"
        save_request(task, status="SUBMITTED")
        audit(user["user_id"], "UPLOAD_REQUEST", "maintenance_request", task["request_id"], {})
        saved.append(task)
    return {"saved": len(saved), "requests": saved}


def save_uploaded_coa(rows: list[dict], filename: str, user: dict) -> dict:
    from backend.database import save_coa_upload

    dates = sorted({str(t.get("date"))[:10] for t in rows if t.get("date")})
    for planning_date in dates:
        date_rows = [t for t in rows if str(t.get("date"))[:10] == planning_date]
        save_coa_upload(filename, planning_date, date_rows, user["user_id"])
        audit(
            user["user_id"],
            "UPLOAD_COA",
            "coa_upload",
            planning_date,
            {"filename": filename, "row_count": len(date_rows)},
        )
    return {"saved": len(rows), "planning_dates": dates}


def _section_lookup() -> dict[str, dict]:
    data = normalize_section_master(load_all_data()["section_master"])
    return {s["section_id"]: s for s in data}


def generate_and_persist_plan(planning_date: str, actor: str = "SYSTEM") -> dict:
    data = load_all_data()
    tasks = [json.loads(r["data_json"]) for r in list_requests() if r["status"] not in {"APPROVED", "REJECTED", "COMPLETED"}]
    # Prefer the latest uploaded COA for the requested date, otherwise use bundled demo COA.
    coa_rows = latest_coa_for_date(planning_date)
    if coa_rows:
        trains = coa_rows
    else:
        trains = normalize_trains(filter_by_date(data["coa"], "Date", planning_date))
    blocks = normalize_existing_blocks(filter_by_date(data["existing_blocks"], "Block_Date", planning_date))
    if not tasks:
        # No application submissions yet: use bundled demo tasks for a convincing local demo.
        tasks = normalize_maintenance_tasks(data["tms"], data["tdms"], data["smms"])
    result = generate_block_plan(tasks, trains, blocks, planning_date)

    # Clear old recommendations for this planning date that are still pending/recommended.
    for old in list_blocks(planning_date, ("PENDING_APPROVAL", "RECOMMENDED")):
        update_block(old["block_id"], status="SUPERSEDED")

    assignments = result["optimization"]["assignments"]
    grouped: dict[tuple, list] = {}
    for assignment in assignments:
        key = (
            assignment["section_id"],
            assignment["block_start"],
            assignment["block_end"],
        )
        grouped.setdefault(key, []).append(assignment)

    request_map = {str(t.get("request_id")): t for t in tasks}
    created_blocks = []
    counters = 0
    for (section_id, start, end), group in grouped.items():
        counters += 1
        block_id = f"VX-{planning_date.replace('-', '')}-{counters:03d}"
        score = max(float(a["priority_score"]) for a in group)
        priority = max((a["priority"] for a in group), key=_priority_rank)
        details = []
        for a in group:
            task = request_map.get(a["task_id"], {})
            details.append({
                "task_id": a["task_id"],
                "department": a["department"],
                "priority": a["priority"],
                "priority_score": a["priority_score"],
                "location": task.get("location"),
                "work_description": task.get("work_description"),
                "asset_id": task.get("asset_id"),
                "asset_type": task.get("asset_type"),
                "maintenance_category": task.get("maintenance_category"),
                "defect_severity": task.get("defect_severity"),
                "failure_risk": task.get("failure_risk"),
                "safety_related": task.get("safety_related"),
                "asset_operational_status": task.get("asset_operational_status"),
                "estimated_duration_minutes": task.get("estimated_duration_minutes"),
                "required_resources": task.get("required_resources"),
                "preferred_date": task.get("preferred_date"),
                "preferred_start_time": task.get("preferred_start_time"),
                "preferred_end_time": task.get("preferred_end_time"),
            })
        block = {
            "block_id": block_id,
            "planning_date": planning_date,
            "section_id": section_id,
            "start_time": start,
            "end_time": end,
            "duration_minutes": time_to_minutes(end) - time_to_minutes(start),
            "priority": priority,
            "priority_score": score,
            "status": "PENDING_APPROVAL",
            "coordination": any(a.get("coordination") for a in group),
            "existing_block": any(a.get("existing_block") for a in group),
            "block_calendar_id": next((a.get("block_calendar_id") for a in group if a.get("block_calendar_id")), None),
            "data": {"tasks": details},
        }
        save_block(block)
        created_blocks.append(block)
        for detail in details:
            update_request_status(detail["task_id"], "PENDING_APPROVAL", block_id=block_id)

    audit(actor, "GENERATE_PLAN", "planning_run", planning_date, {"assignments": len(assignments), "blocks": len(created_blocks)})
    return {**result, "blocks_created": len(created_blocks), "persisted_blocks": created_blocks}


def _priority_rank(value: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(value, 0)


def row_from_db_request(row) -> dict:
    data = json.loads(row["data_json"])
    data.update({"request_id": row["request_id"], "status": row["status"], "block_id": row["block_id"], "rejection_reason": row["rejection_reason"]})
    return data


def row_from_db_block(row) -> dict:
    data = json.loads(row["data_json"])
    return {
        "block_id": row["block_id"],
        "planning_date": row["planning_date"],
        "section_id": row["section_id"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "duration_minutes": row["duration_minutes"],
        "priority": row["priority"],
        "priority_score": row["priority_score"],
        "status": row["status"],
        "coordination": bool(row["coordination"]),
        "existing_block": bool(row["existing_block"]),
        "block_calendar_id": row["block_calendar_id"],
        "rejection_reason": row["rejection_reason"],
        "modification_reason": row["modification_reason"],
        "approved_by": row["approved_by"],
        "tasks": data.get("tasks", []),
        "updated_at": row["updated_at"],
    }


def notification_message_for_block(block: dict) -> str:
    tasks = block.get("tasks", [])
    task_ids = ", ".join(t["task_id"] for t in tasks)
    locations = sorted({str(t.get("location") or "").strip() for t in tasks if t.get("location")})
    station_text = ", ".join(locations) if locations else "station/location in request"
    return (
        f"Approved maintenance block at {block['section_id']} ({station_text}) from "
        f"{block['start_time']} to {block['end_time']} on {block['planning_date']}. "
        f"Tasks: {task_ids}."
    )


def approve_block(block_id: str, actor: str) -> dict:
    row = get_block(block_id)
    if not row:
        raise KeyError("Block not found")
    block = row_from_db_block(row)
    if block["status"] not in {"PENDING_APPROVAL", "RECOMMENDED"}:
        raise ValueError("Only pending blocks can be approved")
    update_block(block_id, status="APPROVED", approved_by=actor, rejection_reason=None)
    for task in block["tasks"]:
        update_request_status(task["task_id"], "APPROVED", block_id=block_id, rejection_reason=None)
    for dept in {"TMS", "TDMS", "SMMS", "COA"}:
        add_notification(dept, "Block approved", notification_message_for_block(block), block_id)
    audit(actor, "APPROVE_BLOCK", "block", block_id, {})
    return row_from_db_block(get_block(block_id))


def reject_block(block_id: str, actor: str, reason: str) -> dict:
    row = get_block(block_id)
    if not row:
        raise KeyError("Block not found")
    block = row_from_db_block(row)
    update_block(block_id, status="REJECTED", rejection_reason=reason)
    for task in block["tasks"]:
        update_request_status(task["task_id"], "REJECTED", block_id=block_id, rejection_reason=reason)
    departments = {t["department"] for t in block["tasks"]} | {"COA"}
    for dept in departments:
        add_notification(dept, "Block rejected", f"Block {block_id} was rejected. Reason: {reason}", block_id)
    audit(actor, "REJECT_BLOCK", "block", block_id, {"reason": reason})
    return row_from_db_block(get_block(block_id))


def _all_active_app_blocks(planning_date: str, exclude: str | None = None) -> list[dict]:
    rows = list_blocks(planning_date, ("PENDING_APPROVAL", "RECOMMENDED", "APPROVED"))
    return [row_from_db_block(r) for r in rows if r["block_id"] != exclude]


def alternative_slots(block_id: str) -> dict:
    row = get_block(block_id)
    if not row:
        raise KeyError("Block not found")

    block = row_from_db_block(row)
    section_id = block["section_id"]
    trains = _planning_trains(block["planning_date"])
    base_windows = find_available_slots(
        section_id,
        block["duration_minutes"],
        trains,
        existing_blocks=[],
    )
    active = _all_active_app_blocks(
        block["planning_date"],
        exclude=block_id,
    )

    task_resources = {
        str(t.get("required_resources", "")).strip().lower()
        for t in block["tasks"]
        if t.get("required_resources")
    }

    available = []
    step = 15

    for window in base_windows:
        window_start = time_to_minutes(window["start_time"])
        window_end = time_to_minutes(window["end_time"])
        duration = block["duration_minutes"]
        candidate = window_start

        while candidate + duration <= window_end and len(available) < 100:
            candidate_end = candidate + duration
            conflict = False
            conflict_reason = None

            for other in active:
                other_start = time_to_minutes(other["start_time"])
                other_end = time_to_minutes(other["end_time"])

                if other["section_id"] == section_id and _intervals_overlap(
                    candidate, candidate_end, other_start, other_end
                ):
                    conflict = True
                    conflict_reason = "Section occupied by another active block"
                    break

                other_resources = {
                    str(t.get("required_resources", "")).strip().lower()
                    for t in other["tasks"]
                    if t.get("required_resources")
                }

                if task_resources & other_resources and _intervals_overlap(
                    candidate, candidate_end, other_start, other_end
                ):
                    conflict = True
                    conflict_reason = "Required resource is already occupied"
                    break

            if not conflict:
                available.append(
                    {
                        "start_time": minutes_to_time(candidate),
                        "end_time": minutes_to_time(candidate_end),
                        "duration_minutes": duration,
                        "suitability": (
                            "CURRENT"
                            if candidate == time_to_minutes(block["start_time"])
                            else "AVAILABLE"
                        ),
                    }
                )

            candidate += step

    return {
        "block": block,
        "available_slots": available,
        "constraints": [
            "No train movement may overlap the selected slot.",
            "The section cannot host another active block at the same time.",
            "A repeated resource combination cannot overlap another active block.",
            "Modified block duration must remain unchanged.",
        ],
    }


def _intervals_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _planning_trains(planning_date: str) -> list[dict]:
    uploaded = latest_coa_for_date(planning_date)
    if uploaded:
        return uploaded
    data = load_all_data()
    return normalize_trains(filter_by_date(data["coa"], "Date", planning_date))


def modify_block(block_id: str, start_time: str, end_time: str, actor: str, reason: str = "") -> dict:
    row = get_block(block_id)
    if not row:
        raise KeyError("Block not found")
    block = row_from_db_block(row)
    if block["status"] not in {"PENDING_APPROVAL", "RECOMMENDED"}:
        raise ValueError("Only pending blocks can be modified")
    if not (_valid_time(start_time) and _valid_time(end_time)) or time_to_minutes(end_time) <= time_to_minutes(start_time):
        raise ValueError("Invalid modification time range")
    duration = time_to_minutes(end_time) - time_to_minutes(start_time)
    if duration != block["duration_minutes"]:
        raise ValueError("Modified block must preserve the required duration")
    alternatives = alternative_slots(block_id)
    if not any(s["start_time"] == start_time and s["end_time"] == end_time for s in alternatives["available_slots"]):
        raise ValueError("Selected time is not a currently feasible slot")
    update_block(block_id, start_time=start_time, end_time=end_time, modification_reason=reason, status="PENDING_APPROVAL")
    audit(actor, "MODIFY_BLOCK", "block", block_id, {"start_time": start_time, "end_time": end_time, "reason": reason})
    return row_from_db_block(get_block(block_id))


def dashboard_summary(user_department: str, planning_date: str) -> dict:
    blocks = [row_from_db_block(r) for r in list_blocks(planning_date)]
    if user_department in {"TMS", "TDMS", "SMMS"} and user_department != "TDMS":
        visible = [b for b in blocks if user_department in {t.get("department") for t in b["tasks"]}]
    else:
        visible = blocks
    reqs = [row_from_db_request(r) for r in list_requests(user_department if user_department in {"TMS", "TDMS", "SMMS"} else None)]
    notifications = []
    return {
        "planning_date": planning_date,
        "eligible_blocks": len(visible),
        "pending_approval": len([b for b in visible if b["status"] == "PENDING_APPROVAL"]),
        "approved": len([b for b in visible if b["status"] == "APPROVED"]),
        "scheduled_tasks": len([r for r in reqs if r["status"] in {"PENDING_APPROVAL", "APPROVED"}]),
        "requests": reqs[:20],
        "blocks": sorted(visible, key=lambda b: (-float(b["priority_score"]), b["start_time"])),
    }


def seed_demo_dataset() -> dict:
    data = load_all_data()
    # Seed maintenance requests only if there are none.
    if not list_requests():
        tasks = normalize_maintenance_tasks(data["tms"], data["tdms"], data["smms"])
        for task in tasks:
            task["request_status"] = "SUBMITTED"
            save_request(task, status="SUBMITTED")
    return {"maintenance_requests": len(list_requests())}


def build_template(kind: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    headers = maintenance_headers() if kind == "maintenance" else coa_headers()
    ws.append(headers)
    if kind == "maintenance":
        ws.append([
            "TMS-NEW", "TMS", "TMS", "STN01", "SEC01", "TRK-001", "TRACK",
            "Replace worn rail", "Corrective", "DEF-0001", "HIGH", "HIGH", True,
            "RESTRICTED", 1, "2026-08-01", "2026-09-01", False, 120,
            "6 workers, tamping machine", True, "PARTIAL", "2026-09-01", "05:00", "07:00", "SUBMITTED"
        ])
    else:
        ws.append([
            "T001", "EXPRESS", "2026-09-01", "R001", "SEC01", "STN01", "STN02",
            "10:00", "11:00", "DOWN", "HIGH", "SCHEDULED"
        ])
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
