Set-Location $PSScriptRoot
. .\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\src"
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
