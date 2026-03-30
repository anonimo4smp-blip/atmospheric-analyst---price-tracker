param(
    [string]$OutputDir = ".\snapshots"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$snapshotDir = Join-Path $OutputDir $timestamp

New-Item -ItemType Directory -Force -Path $snapshotDir | Out-Null

Write-Host "Exportando estado de Docker Compose..."
docker compose ps > (Join-Path $snapshotDir "compose-ps.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo exportar 'docker compose ps'."
}

docker compose config > (Join-Path $snapshotDir "compose-resolved.yml")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo exportar 'docker compose config'."
}

Write-Host "Exportando informacion adicional..."
docker version > (Join-Path $snapshotDir "docker-version.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo exportar 'docker version'."
}

docker compose version > (Join-Path $snapshotDir "compose-version.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo exportar 'docker compose version'."
}

if (Test-Path ".\.env") {
    Write-Host "Copiando .env (incluye secretos, proteger este archivo)."
    Copy-Item ".\.env" (Join-Path $snapshotDir ".env.snapshot") -Force
}

Write-Host "Snapshot generado en: $snapshotDir"
