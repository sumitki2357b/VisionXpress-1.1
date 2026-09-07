from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import backend.database as database
from backend.api.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "visionxpress_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, department: str, user_id: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={
            "department": department,
            "user_id": user_id,
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_login_manual_request_tracking_and_bdms_approval(client):
    tms = login(client, "TMS", "TMS001", "TMS@123")
    headers = {"Authorization": f"Bearer {tms['token']}"}

    manual = {
        "location": "STN01",
        "section_id": "SEC01",
        "asset_id": "TRK-NEW-01",
        "asset_type": "TRACK",
        "work_description": "Replace worn rail",
        "maintenance_category": "Corrective",
        "defect_id": "DEF-NEW-01",
        "defect_severity": "HIGH",
        "failure_risk": "HIGH",
        "safety_related": True,
        "asset_operational_status": "RESTRICTED",
        "affected_asset_quantity": 1,
        "last_maintenance_date": "2026-08-01",
        "due_date": "2026-09-01",
        "overdue": False,
        "estimated_duration_minutes": 120,
        "required_resources": "6 workers, tamping machine",
        "requires_block": True,
        "block_type_required": "PARTIAL",
        "preferred_date": "2026-09-01",
        "preferred_start_time": "05:00",
        "preferred_end_time": "07:00",
    }

    response = client.post(
        "/api/maintenance/manual",
        headers=headers,
        json=manual,
    )
    assert response.status_code == 200
    task_id = response.json()["request"]["request_id"]

    tracked = client.get(
        f"/api/maintenance/requests/{task_id}",
        headers=headers,
    )
    assert tracked.status_code == 200
    assert tracked.json()["status"] == "SUBMITTED"
    assert tracked.json()["department"] == "TMS"

    bdms = login(client, "BDMS", "BDMS001", "BDMS@123")
    bdms_headers = {"Authorization": f"Bearer {bdms['token']}"}

    generated = client.post(
        "/api/planning/generate",
        headers=bdms_headers,
        json={"planning_date": "2026-09-01"},
    )
    assert generated.status_code == 200
    assert generated.json()["blocks_created"] >= 1

    pending = client.get(
        "/api/blocks?planning_date=2026-09-01&status=PENDING_APPROVAL",
        headers=bdms_headers,
    )
    assert pending.status_code == 200
    blocks = pending.json()["blocks"]
    assert blocks

    block_id = next(
        block["block_id"]
        for block in blocks
        if task_id in {task["task_id"] for task in block["tasks"]}
    )

    detail = client.get(
        f"/api/blocks/{block_id}",
        headers=bdms_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "PENDING_APPROVAL"

    slots = client.get(
        f"/api/blocks/{block_id}/slots",
        headers=bdms_headers,
    )
    assert slots.status_code == 200
    assert "available_slots" in slots.json()

    approved = client.post(
        f"/api/blocks/{block_id}/approve",
        headers=bdms_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    notifications = client.get(
        "/api/notifications",
        headers=headers,
    )
    assert notifications.status_code == 200
    assert any(n["block_id"] == block_id for n in notifications.json()["notifications"])


def test_maintenance_upload_rejects_invalid_row(client, tmp_path):
    tms = login(client, "TMS", "TMS001", "TMS@123")
    headers = {"Authorization": f"Bearer {tms['token']}"}

    path = tmp_path / "invalid.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Request_id", "Department", "Source_system", "Location", "Section_id", "Asset_id", "Asset_type", "Work_description", "Maintenance_category", "Defect_id", "Defect_severity", "Failure_risk", "Safety_related", "Asset_operational_status", "Affected_asset_quantity", "Last_maintenance_date", "Due_date", "Overdue", "Estimated_duration_minutes", "Required_resources", "Requires_block", "Block_type_required"])
    ws.append(["TMS-BAD", "TMS", "TMS", "STN01", "SEC01", "TRK-BAD", "TRACK", "Invalid duration", "Corrective", "DEF-BAD", "HIGH", "HIGH", "FALSE", "RESTRICTED", 1, "2026-08-01", "2026-09-01", "FALSE", -10, "6 workers, tamping machine", "TRUE", "PARTIAL"])
    wb.save(path)

    with path.open("rb") as handle:
        response = client.post(
            "/api/maintenance/upload",
            headers=headers,
            files={"file": ("invalid.xlsx", handle, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["valid"] is False
    assert body["invalid_count"] == 1
    assert any("estimated_duration_minutes" in err for err in body["errors"][0]["errors"])
