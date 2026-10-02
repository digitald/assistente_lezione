@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -X utf8 main.py --desktop
if errorlevel 1 pause
