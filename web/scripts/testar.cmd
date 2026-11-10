@echo off
rem Testes da aplicacao: API, componentes e integracao em navegador real.
cd /d "%~dp0..\backend"
..\..\.venv\Scripts\python -m pytest tests -q -p no:cacheprovider || exit /b 1
cd ..\frontend
call npx vitest run || exit /b 1
call npm run build || exit /b 1
call npx playwright test || exit /b 1
