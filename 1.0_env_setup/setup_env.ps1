$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "[1/4] Creating virtual environment..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& ".venv\Scripts\Activate.ps1"
Write-Host "[2/4] Upgrading pip..."
python -m pip install --upgrade pip
Write-Host "[3/4] Installing project dependencies..."
pip install -r requirements.txt
Write-Host "[4/4] Validating committed configuration templates..."
python 1.5_security/config_validator.py --check-example

Write-Host "Setup completed successfully."
Write-Host "Copy .env.example to .env and .streamlit/secrets.example.toml to .streamlit/secrets.toml, then run the Streamlit app."
