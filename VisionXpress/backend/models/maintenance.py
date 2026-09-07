from pydantic import BaseModel
from typing import Optional


class MaintenanceRequest(BaseModel):
    request_id: str
    department: str
    source_system: str

    location: str
    section_id: str

    asset_id: str
    asset_type: str

    work_description: Optional[str] = None
    maintenance_category: str

    defect_id: Optional[str] = None
    defect_severity: Optional[str] = None
    failure_risk: Optional[str] = None

    safety_related: bool
    asset_operational_status: str

    affected_asset_quantity: Optional[int] = None

    last_maintenance_date: Optional[str] = None
    due_date: Optional[str] = None
    overdue: bool

    estimated_duration_minutes: int
    required_resources: Optional[str] = None

    requires_block: bool
    block_type_required: str

    preferred_date: Optional[str] = None
    preferred_start_time: Optional[str] = None
    preferred_end_time: Optional[str] = None

    request_status: str = "PENDING"