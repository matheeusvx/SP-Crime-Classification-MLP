@echo off
rem Interface em http://127.0.0.1:5173 com proxy de /api para a porta 8000.
cd /d "%~dp0..\frontend"
call npm run dev -- --host 127.0.0.1
