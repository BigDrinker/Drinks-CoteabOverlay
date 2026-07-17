@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run scripts\setup-dev.bat first.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

pushd frontend
call npm ci
if errorlevel 1 goto :error
call npm run build
if errorlevel 1 goto :error
popd

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release rmdir /s /q release
mkdir release

pyinstaller --noconfirm --clean CoteabMacro.spec
if errorlevel 1 goto :error

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\Coteab Macro\*' -DestinationPath 'release\Coteab-Macro-Overlay-v2.2.1-Windows.zip' -Force"
if errorlevel 1 goto :error

echo.
echo Release created:
echo %CD%\release\Coteab-Macro-Overlay-v2.2.1-Windows.zip
pause
exit /b 0

:error
echo.
echo BUILD FAILED.
pause
exit /b 1
