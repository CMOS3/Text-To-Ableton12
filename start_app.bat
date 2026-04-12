@echo off
setlocal
cd /d %~dp0

echo ==========================================
echo   Starting Ableton MCP Ecosystem
echo ==========================================

:: 1. Start backend in a new window
echo [BACKEND] Launching FastAPI at http://127.0.0.1:8000
start "Ableton Backend" cmd /k "call .venv\Scripts\activate && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

:: 2. Wait for backend to be ready
echo [WAIT] Waiting for backend to initialize (5s)...
timeout /t 5 /nobreak > nul

:: 3. Start Electron frontend in a new window
echo [FRONTEND] Launching Electron App...
start "Ableton Frontend" cmd /k "cd frontend && npm start"

echo.
echo ==========================================
echo   Both services are starting...
echo   Close this window to finish.
echo ==========================================
timeout /t 3 > nul
exit
