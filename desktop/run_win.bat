@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw "%~dp0app.py") || (python "%~dp0app.py")