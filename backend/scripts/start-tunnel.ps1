[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Error "ngrok no esta instalado o no esta en PATH."
    Write-Error "Ejecuta: winget install --id Ngrok.Ngrok -e"
    exit 1
}

$fixedDomain = "terpenic-dampishly-reda.ngrok-free.dev"
$fixedUrl = "https://$fixedDomain"

Write-Host "Abriendo tunnel ngrok fijo hacia http://localhost:8000 ..."
Write-Host "Dominio fijo: $fixedUrl"
Write-Host "Webhook esperado: $fixedUrl/payments/webhook/mercadopago"

try {
    ngrok http --url=$fixedUrl 8000
}
catch {
    Write-Warning "Fallo con --url. Reintentando con --domain ..."
    ngrok http --domain=$fixedDomain 8000
}
