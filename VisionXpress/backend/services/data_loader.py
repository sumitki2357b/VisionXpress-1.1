from pathlib import Path

from backend.services.input_loader import (
    load_maintenance_file,
    load_coa_file,
    load_file,
)


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
MAINTENANCE_DIR = DATA_DIR / "maintenance"
COA_DIR = DATA_DIR / "coa"


def load_all_data() -> dict:
    """
    Load all VisionXpress datasets.
    """

    return {
        "tms": load_maintenance_file(
            str(MAINTENANCE_DIR / "tms all.xlsx")
        ),

        "tdms": load_maintenance_file(
            str(MAINTENANCE_DIR / "tdms all.xlsx")
        ),

        "smms": load_maintenance_file(
            str(MAINTENANCE_DIR / "smms.xlsx")
        ),

        "coa": load_coa_file(
            str(COA_DIR / "coa.xlsx")
        ),

        "existing_blocks": load_file(
            str(DATA_DIR / "existing_blocks.xlsx")
        ),

        "section_master": load_file(
            str(DATA_DIR / "section_master.xlsx")
        ),
    }