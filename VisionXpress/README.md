# VisionXpress

VisionXpress is a local-first smart railway maintenance block planning system for SIH demonstration. It combines TMS, TDMS, SMMS maintenance requests, COA train movement data, existing block calendars and section master data.

## Highlights

- Fixed role-based login for TMS, TDMS, SMMS, COA and BDMS
- Manual maintenance request entry
- CSV/XLSX maintenance request upload with row-level validation
- COA CSV/XLSX upload and history
- Planning-date filtering
- Priority-aware maintenance planning
- Train conflict avoidance
- Section overlap prevention
- Resource overlap prevention
- Cross-department coordination
- BDMS approve / reject / modify workflow
- Alternative feasible block slots for manual modification
- In-app notifications after approval
- Task tracking by Task ID
- SQLite persistence for the local demo
- Built-in synthetic demo dataset
- Automated pytest regression suite

## Demo accounts

| Department | User ID | Password |
|---|---|---|
| TMS | TMS001 | TMS@123 |
| TDMS | TDMS001 | TDMS@123 |
| SMMS | SMMS001 | SMMS@123 |
| COA | COA001 | COA@123 |
| BDMS | BDMS001 | BDMS@123 |

These are demonstration credentials only.

## Run locally

Create/activate a Python virtual environment and install requirements:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the application:

```powershell
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

Open:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

## Quick demo flow

1. Log in as BDMS and click **Load demo** if you want a populated local demo dataset, or log in as TMS/TDMS/SMMS and submit requests.
2. Log in as COA and upload a COA schedule when demonstrating custom schedules.
3. Log in as TDMS/BDMS and generate or refresh the plan for the chosen date.
4. Open a recommended block to inspect every maintenance task, asset and resource requirement.
5. As BDMS, modify the block by selecting a feasible alternative slot, or approve/reject it.
6. Log in as TMS/TDMS/SMMS/COA to see the approval alert.
7. Use **Track Request** with a Task ID to demonstrate end-to-end request status.

## Data

The `data/` folder contains synthetic demonstration data. `existing_blocks.xlsx` and `section_master.xlsx` are treated as reference data. User uploads are stored in SQLite and temporary upload files are removed after parsing.

## Tests

```powershell
python -m pytest
```

The baseline backend suite is intentionally retained and extended with API workflow tests.
