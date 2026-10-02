@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -X utf8 web_app.py --demo --port 8766
if errorlevel 1 pause
