@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run scripts\setup-dev.bat first.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python main.py
if errorlevel 1 pause
