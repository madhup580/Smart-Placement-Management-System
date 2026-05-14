# PowerShell script to start Flask app with venv
$venvPath = "C:\Users\Vyshnavi\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "✅ Virtual environment activated"
} else {
    Write-Host "❌ Virtual environment not found at $venvPath"
    exit 1
}

Set-Location $PSScriptRoot
Write-Host "✅ Starting Flask app..."
python app.py

