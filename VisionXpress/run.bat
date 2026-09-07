@echo off
cd /d "%~dp0"
if not exist "app_data" mkdir "app_data"
call ".venv\Scripts\activate.bat" 2>nul
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
