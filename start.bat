@echo off
REM Quick Start Script for MediAssist AI (Windows)
REM This script sets up and runs both backend and frontend

echo.
echo MediAssist AI - Quick Start
echo ===========================
echo.

REM Check if backend is running
echo Checking if backend is running...
curl -s http://127.0.0.1:8000/ > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend is already running
) else (
    echo [INFO] Backend is not running. Starting it...
    
    REM Start backend
    cd backend
    
    if not exist "venv" (
        echo Creating Python virtual environment...
        python -m venv venv
    )
    
    REM Activate venv
    call venv\Scripts\activate.bat
    
    echo Installing backend dependencies...
    pip install -r requirements.txt > nul 2>&1
    
    echo [OK] Backend dependencies installed
    echo Starting FastAPI server...
    
    REM Start backend in new window
    start cmd /k "cd /d %cd% && venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"
    
    timeout /t 3 /nobreak
    cd ..
)

echo.
echo Starting frontend...
cd frontend

if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

echo [OK] Frontend dependencies ready
echo Starting Vite development server...
echo.
echo Open your browser and navigate to: http://localhost:5173
echo.

call npm run dev

cd ..
