@echo off
setlocal

set NAME=E2-HUD-Designer
if not "%~1"=="" set NAME=%~1

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set MAIN_PATH=%ROOT_DIR%\main.py

if not exist "%MAIN_PATH%" (
  echo ERROR: main.py not found at "%MAIN_PATH%"
  exit /b 1
)

pushd "%ROOT_DIR%" >nul
python -m pip install --upgrade pyinstaller >nul
pyinstaller --noconfirm --onefile --windowed --name "%NAME%" "%MAIN_PATH%"
if errorlevel 1 (
  popd >nul
  exit /b 1
)
popd >nul

echo Build complete. Output in dist\%NAME%.exe
