from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import FRONTEND_DIR
from backend.database import (
    create_session,
    delete_session,
    get_user_by_credentials,
    get_user_by_token,
    init_db,
    list_blocks,
    list_coa_uploads,
    list_notifications,
    mark_notification_read,
    get_block,
    list_requests,
)
from backend.services.application_service import (
    alternative_slots,
    approve_block,
    build_template,
    create_manual_request,
    dashboard_summary,
    generate_and_persist_plan,
    load_uploaded_rows,
    modify_block,
    reject_block,
    row_from_db_block,
    row_from_db_request,
    save_uploaded_coa,
    save_uploaded_maintenance,
    seed_demo_dataset,
    validate_coa_upload,
    validate_maintenance_upload,
)
from backend.services.data_loader import load_all_data
from backend.services.data_normalizer import normalize_section_master

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="VisionXpress", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return dict(user)


class LoginPayload(BaseModel):
    department: str
    user_id: str
    password: str


class ManualMaintenancePayload(BaseModel):
    location: str
    section_id: str
    asset_id: str
    asset_type: str
    work_description: str
    maintenance_category: str
    defect_id: str = ""
    defect_severity: str
    failure_risk: str
    safety_related: bool
    asset_operational_status: str
    affected_asset_quantity: int = 1
    last_maintenance_date: str = ""
    due_date: str = ""
    overdue: bool = False
    estimated_duration_minutes: int = Field(gt=0)
    required_resources: str = ""
    requires_block: bool = True
    block_type_required: str = "PARTIAL"
    preferred_date: str = ""
    preferred_start_time: str = ""
    preferred_end_time: str = ""
    request_id: str | None = None


class GeneratePayload(BaseModel):
    planning_date: str


class ModifyPayload(BaseModel):
    start_time: str
    end_time: str
    reason: str = ""


class RejectPayload(BaseModel):
    reason: str = Field(min_length=3)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "VisionXpress"}


@app.get("/api/sections")
def sections(user=Depends(current_user)):
    rows = normalize_section_master(load_all_data()["section_master"])
    return {"sections": rows}


@app.post("/api/auth/login")
def login(payload: LoginPayload):
    department = payload.department.strip().upper()
    user = get_user_by_credentials(department, payload.user_id.strip(), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid department, user ID or password")
    token = create_session(user)
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "department": user["department"],
            "role": user["role"],
        },
    }


@app.post("/api/auth/logout")
def logout(authorization: Annotated[str | None, Header()] = None):
    if authorization and authorization.lower().startswith("bearer "):
        delete_session(authorization.split(" ", 1)[1])
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"user_id": user["user_id"], "department": user["department"], "role": user["role"]}


@app.post("/api/maintenance/manual")
def submit_manual(payload: ManualMaintenancePayload, user=Depends(current_user)):
    if user["role"] != "MAINTENANCE":
        raise HTTPException(status_code=403, detail="Maintenance submission is available only to TMS/TDMS/SMMS")
    result = create_manual_request(payload.model_dump(), user)
    if not result["valid"]:
        return JSONResponse(status_code=422, content=result)
    return result


@app.post("/api/maintenance/upload")
async def upload_maintenance(file: UploadFile = File(...), user=Depends(current_user)):
    if user["role"] != "MAINTENANCE":
        raise HTTPException(status_code=403, detail="Maintenance upload is available only to TMS/TDMS/SMMS")
    if Path(file.filename or "").suffix.lower() not in {".xlsx", ".xlsm", ".csv"}:
        raise HTTPException(status_code=400, detail="Use CSV, XLSX or XLSM files")
    rows = load_uploaded_rows(await file.read(), file.filename or "upload.xlsx")
    sections = load_all_data()["section_master"]
    validation = validate_maintenance_upload(rows, user["department"], sections)
    if not validation["valid"]:
        return JSONResponse(status_code=422, content=validation | {"filename": file.filename})
    saved = save_uploaded_maintenance(validation["tasks"], user)
    return {"valid": True, "filename": file.filename, **saved}


@app.get("/api/maintenance/requests")
def maintenance_requests(task_id: str | None = Query(default=None), user=Depends(current_user)):
    if user["role"] == "MAINTENANCE":
        rows = list_requests(user["department"], task_id)
    else:
        rows = list_requests(None, task_id)
    return {"requests": [row_from_db_request(r) for r in rows]}


@app.get("/api/maintenance/requests/{task_id}")
def maintenance_request(task_id: str, user=Depends(current_user)):
    rows = list_requests(None, task_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    item = row_from_db_request(rows[0])
    if user["role"] == "MAINTENANCE" and item["department"] != user["department"]:
        raise HTTPException(status_code=403, detail="You cannot view another department's request")
    return item


@app.post("/api/coa/upload")
async def upload_coa(file: UploadFile = File(...), user=Depends(current_user)):
    if user["role"] != "COA":
        raise HTTPException(status_code=403, detail="COA access only")
    if Path(file.filename or "").suffix.lower() not in {".xlsx", ".xlsm", ".csv"}:
        raise HTTPException(status_code=400, detail="Use CSV, XLSX or XLSM files")
    rows = load_uploaded_rows(await file.read(), file.filename or "coa.xlsx")
    sections = load_all_data()["section_master"]
    validation = validate_coa_upload(rows, sections)
    if not validation["valid"]:
        return JSONResponse(status_code=422, content=validation | {"filename": file.filename})
    result = save_uploaded_coa(validation["trains"], file.filename or "coa.xlsx", user)
    return {"valid": True, "filename": file.filename, **result}


@app.get("/api/coa/uploads")
def coa_uploads(user=Depends(current_user)):
    if user["role"] != "COA":
        raise HTTPException(status_code=403, detail="COA access only")
    return {"uploads": [dict(r) for r in list_coa_uploads()]}


@app.post("/api/planning/generate")
def generate_plan(payload: GeneratePayload, user=Depends(current_user)):
    if user["role"] not in {"BDMS", "MAINTENANCE", "COA"}:
        raise HTTPException(status_code=403, detail="Not allowed to generate a plan")
    return generate_and_persist_plan(payload.planning_date, user["user_id"])


@app.get("/api/dashboard")
def dashboard(planning_date: str = "2026-09-01", user=Depends(current_user)):
    return dashboard_summary(user["department"], planning_date)


@app.get("/api/blocks")
def blocks(planning_date: str = "2026-09-01", status: str | None = None, user=Depends(current_user)):
    rows = list_blocks(planning_date, (status,) if status else None)
    result = [row_from_db_block(r) for r in rows]
    if user["role"] == "MAINTENANCE" and user["department"] != "TDMS":
        result = [b for b in result if user["department"] in {t.get("department") for t in b["tasks"]}]
    return {"blocks": result}


@app.get("/api/blocks/{block_id}")
def block_detail(block_id: str, user=Depends(current_user)):
    row = get_block(block_id)
    if not row:
        raise HTTPException(status_code=404, detail="Block not found")
    block = row_from_db_block(row)
    if user["role"] == "MAINTENANCE" and user["department"] != "TDMS" and user["department"] not in {t.get("department") for t in block["tasks"]}:
        raise HTTPException(status_code=403, detail="You cannot view this block")
    return block


@app.get("/api/blocks/{block_id}/slots")
def block_slots(block_id: str, user=Depends(current_user)):
    if user["role"] != "BDMS":
        raise HTTPException(status_code=403, detail="BDMS access only")
    try:
        return alternative_slots(block_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/blocks/{block_id}/modify")
def modify(block_id: str, payload: ModifyPayload, user=Depends(current_user)):
    if user["role"] != "BDMS":
        raise HTTPException(status_code=403, detail="BDMS access only")
    try:
        return modify_block(block_id, payload.start_time, payload.end_time, user["user_id"], payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/blocks/{block_id}/approve")
def approve(block_id: str, user=Depends(current_user)):
    if user["role"] != "BDMS":
        raise HTTPException(status_code=403, detail="BDMS access only")
    try:
        return approve_block(block_id, user["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/blocks/{block_id}/reject")
def reject(block_id: str, payload: RejectPayload, user=Depends(current_user)):
    if user["role"] != "BDMS":
        raise HTTPException(status_code=403, detail="BDMS access only")
    try:
        return reject_block(block_id, user["user_id"], payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/notifications")
def notifications(user=Depends(current_user)):
    return {"notifications": [dict(r) for r in list_notifications(user["department"])]}


@app.post("/api/notifications/{notification_id}/read")
def notification_read(notification_id: int, user=Depends(current_user)):
    mark_notification_read(notification_id, user["department"])
    return {"ok": True}


@app.post("/api/demo/load")
def demo_load(user=Depends(current_user)):
    if user["role"] != "BDMS":
        raise HTTPException(status_code=403, detail="BDMS access only")
    result = seed_demo_dataset()
    return result


@app.get("/api/templates/maintenance")
def maintenance_template(user=Depends(current_user)):
    if user["role"] != "MAINTENANCE":
        raise HTTPException(status_code=403, detail="Maintenance access only")
    content = build_template("maintenance")
    return StreamingResponse(iter([content]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=maintenance_template.xlsx"})


@app.get("/api/templates/coa")
def coa_template(user=Depends(current_user)):
    if user["role"] != "COA":
        raise HTTPException(status_code=403, detail="COA access only")
    content = build_template("coa")
    return StreamingResponse(iter([content]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=coa_template.xlsx"})


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app.js", include_in_schema=False)
def app_js():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/styles.css", include_in_schema=False)
def styles_css():
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")
