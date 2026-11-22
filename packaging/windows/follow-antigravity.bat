@echo off
cd /d "%~dp0"
if exist "dist\GeminiCatgirl\GeminiCatgirl.exe" (
  start "" "dist\GeminiCatgirl\GeminiCatgirl.exe"
) else if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
) else (
  echo Run setup.bat first.
  pause
)
