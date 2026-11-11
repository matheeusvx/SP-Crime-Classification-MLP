@echo off
rem API em http://127.0.0.1:8000 (documentacao em /api/docs).
cd /d "%~dp0..\.."
.venv\Scripts\python -m uvicorn app.main:app --app-dir web\backend --host 127.0.0.1 --port 8000 --no-access-log
