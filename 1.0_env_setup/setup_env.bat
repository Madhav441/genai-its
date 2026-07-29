@echo off
setlocal
cd /d "%~dp0\.."

echo [1/4] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" py -m venv .venv

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

echo [2/4] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/4] Installing project dependencies...
pip install -r requirements.txt
if errorlevel 1 goto :error

echo [4/4] Validating committed configuration templates...
python 1.5_security\config_validator.py --check-example
if errorlevel 1 goto :error

echo.
echo Setup completed successfully.
echo Next steps:
echo   1. Copy .env.example to .env and add your real values.
echo   2. Copy .streamlit\secrets.example.toml to .streamlit\secrets.toml.
echo   3. Run: streamlit run 1.1_interface\streamlit_app.py
exit /b 0

:error
echo.
echo Setup failed. Review the error above.
exit /b 1
