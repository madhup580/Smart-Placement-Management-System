@echo off
REM Activate venv and start Flask app
call C:\Users\Vyshnavi\venv\Scripts\activate.bat
cd /d "%~dp0"
python app.py
pause

