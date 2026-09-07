from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "app_data" / "visionxpress.db"
FRONTEND_DIR = BASE_DIR / "frontend"

DEMO_USERS = {
    "TMS": {
        "user_id": "TMS001",
        "password": "TMS@123",
        "role": "MAINTENANCE",
    },
    "TDMS": {
        "user_id": "TDMS001",
        "password": "TDMS@123",
        "role": "MAINTENANCE",
    },
    "SMMS": {
        "user_id": "SMMS001",
        "password": "SMMS@123",
        "role": "MAINTENANCE",
    },
    "COA": {
        "user_id": "COA001",
        "password": "COA@123",
        "role": "COA",
    },
    "BDMS": {
        "user_id": "BDMS001",
        "password": "BDMS@123",
        "role": "BDMS",
    },
}

VALID_DEPARTMENTS = tuple(DEMO_USERS.keys())
