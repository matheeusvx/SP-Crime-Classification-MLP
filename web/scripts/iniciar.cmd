@echo off
rem Abre backend e frontend em janelas separadas e depois o navegador.
start "GS API" cmd /k "%~dp0iniciar-backend.cmd"
start "GS Frontend" cmd /k "%~dp0iniciar-frontend.cmd"
timeout /t 15 /nobreak >nul
start "" http://127.0.0.1:5173
