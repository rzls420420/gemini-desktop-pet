@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install PyQt5 pyinstaller
if errorlevel 1 goto fail
echo Setup complete. Run standalone.bat or follow-antigravity.bat.
pause
exit /b 0
:fail
echo Setup failed. Check Python 3, network access, and the errors above.
pause
exit /b 1
