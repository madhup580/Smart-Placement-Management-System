@echo off
echo ========================================
echo Starting Interview Preparation Platform
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo [1/3] Checking database connection...
python test_connection.py
if errorlevel 1 (
    echo.
    echo WARNING: Database connection test failed
    echo Please check your database configuration
    echo.
    pause
)

echo.
echo [2/3] Starting Flask server...
echo Server will be available at: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.

python app.py

pause

