@echo off
rem Instala dependencias Python (.venv) e JavaScript. Requer Python 3.12 e Node 22.
cd /d "%~dp0..\.."
if not exist .venv\Scripts\python.exe (python -m venv .venv || exit /b 1)
.venv\Scripts\python -m pip install --disable-pip-version-check -r requirements-web-dev.txt || exit /b 1
cd web\frontend
call npm ci || exit /b 1
echo Instalacao concluida.
