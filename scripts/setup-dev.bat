@echo off
setlocal
cd /d "%~dp0.."

py -3.12 -m venv .venv
if errorlevel 1 goto :error
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :error

pushd frontend
call npm ci
if errorlevel 1 goto :error
call npm run build
if errorlevel 1 goto :error
popd

echo Setup complete. Use scripts\run-dev.bat.
pause
exit /b 0
:error
echo Setup failed.
pause
exit /b 1
