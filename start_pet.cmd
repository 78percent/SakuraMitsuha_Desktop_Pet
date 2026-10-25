@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Project environment missing. Run setup_env.ps1 first.
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0run_pet.py" %*
exit /b %errorlevel%
