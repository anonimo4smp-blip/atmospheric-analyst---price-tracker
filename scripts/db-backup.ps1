param(
    [string]$OutputDir = ".\backups",
    [switch]$IncludeN8nDb
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "admin" }
$appDbName = if ($env:APP_DB_NAME) { $env:APP_DB_NAME } else { "pricetracker" }
$n8nDbName = if ($env:N8N_DB_NAME) { $env:N8N_DB_NAME } else { "n8n" }

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$appBackupPath = Join-Path $OutputDir "$appDbName-$timestamp.sql"
Write-Host "Generando backup de $appDbName en $appBackupPath ..."
docker compose exec -T postgres pg_dump -U $pgUser -d $appDbName > $appBackupPath
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo generar el backup de $appDbName."
}

if ($IncludeN8nDb) {
    $n8nBackupPath = Join-Path $OutputDir "$n8nDbName-$timestamp.sql"
    Write-Host "Generando backup de $n8nDbName en $n8nBackupPath ..."
    docker compose exec -T postgres pg_dump -U $pgUser -d $n8nDbName > $n8nBackupPath
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo generar el backup de $n8nDbName."
    }
}

Write-Host "Backup completado."
