[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir

if (-not (Get-Command uvicorn -ErrorAction SilentlyContinue)) {
    Write-Error "uvicorn no esta instalado o no esta en PATH. Instala con: pip install uvicorn"
    exit 1
}

Write-Host "Iniciando backend en http://localhost:8000 ..."
Write-Host "Comando: uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
Push-Location $backendDir
try {
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}
finally {
    Pop-Location
}
