from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _clean_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {
        "true", "yes", "y", "1", "t"
    }


def _clean_int(value: Any):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _clean_date(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()[:10]


def normalize_maintenance_tasks(
    tms: list[dict],
    tdms: list[dict],
    smms: list[dict],
) -> list[dict]:

    tasks = []

    for source_tasks in [tms, tdms, smms]:

        for task in source_tasks:

            normalized = {
                "request_id": task.get("Request_id"),
                "department": task.get("Department"),
                "source_system": task.get("Source_system"),

                "location": task.get("Location"),
                "section_id": task.get("Section_id"),

                "asset_id": task.get("Asset_id"),
                "asset_type": task.get("Asset_type"),

                "work_description": task.get("Work_description"),
                "maintenance_category": task.get(
                    "Maintenance_category"
                ),

                "defect_id": task.get("Defect_id"),
                "defect_severity": task.get(
                    "Defect_severity"
                ),

                "failure_risk": task.get("Failure_risk"),
                "safety_related": _clean_bool(
                    task.get("Safety_related")
                ),

                "asset_operational_status": task.get(
                    "Asset_operational_status"
                ),

                "affected_asset_quantity": _clean_int(
                    task.get("Affected_asset_quantity")
                ),

                "last_maintenance_date": _clean_date(
                    task.get("Last_maintenance_date")
                ),

                "due_date": _clean_date(
                    task.get("Due_date")
                ),

                "overdue": _clean_bool(
                    task.get("Overdue")
                ),

                "estimated_duration_minutes": _clean_int(
                    task.get("Estimated_duration_minutes")
                ),

                "required_resources": task.get(
                    "Required_resources"
                ),

                "requires_block": _clean_bool(
                    task.get("Requires_block")
                ),

                "block_type_required": task.get(
                    "Block_type_required"
                ),

                "preferred_date": _clean_date(
                    task.get("Preferred_date")
                ),

                "preferred_start_time": task.get(
                    "Preferred_start_time"
                ),

                "preferred_end_time": task.get(
                    "Preferred_end_time"
                ),

                "request_status": task.get(
                    "Request_status"
                ),
            }

            tasks.append(normalized)

    return tasks


def normalize_trains(
    coa: list[dict],
) -> list[dict]:

    trains = []

    for train in coa:

        normalized = {
            "train_id": train.get("Train_ID"),
            "train_type": train.get("Train_Type"),
            "date": _clean_date(train.get("Date")),

            "route_id": train.get("Route_ID"),

            "section_id": train.get("Section_ID"),

            "start_station": train.get(
                "Start_Station"
            ),

            "end_station": train.get(
                "End_Station"
            ),

            "start_time": train.get(
                "Start_Time"
            ),

            "end_time": train.get(
                "End_Time"
            ),

            "direction": train.get(
                "Direction"
            ),

            "train_priority": train.get(
                "Train_Priority"
            ),

            "operational_status": train.get(
                "Operational_Status"
            ),
        }

        trains.append(normalized)

    return trains


def normalize_existing_blocks(
    blocks: list[dict],
) -> list[dict]:

    normalized_blocks = []

    for block in blocks:

        normalized_blocks.append(
            {
                "block_calendar_id": block.get(
                    "Block_Calendar_ID"
                ),

                "section_id": block.get(
                    "Section_id"
                ),

                "block_date": _clean_date(block.get(
                    "Block_Date"
                )),

                "start_time": block.get(
                    "Start_Time"
                ),

                "end_time": block.get(
                    "End_Time"
                ),

                "approved_for_department": block.get(
                    "Approved_For_Department"
                ),

                "block_status": block.get(
                    "Block_Status"
                ),
            }
        )

    return normalized_blocks


def normalize_section_master(
    sections: list[dict],
) -> list[dict]:

    normalized_sections = []

    for section in sections:

        normalized_sections.append(
            {
                "section_id": section.get(
                    "Section_id"
                ),

                "section_name": section.get(
                    "Section_Name"
                ),

                "zone": section.get(
                    "Zone"
                ),

                "division": section.get(
                    "Division"
                ),

                "route_type": section.get(
                    "Route_Type"
                ),

                "corridor_group": section.get(
                    "Corridor_Group"
                ),
            }
        )

    return normalized_sections
