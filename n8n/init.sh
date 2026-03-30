#!/bin/sh
# Inicialización de n8n.
# El envío de emails se delega al backend: POST /internal/alerts/{id}/send-email
# n8n no necesita credenciales SMTP propias.

log() { echo "[n8n-init] $*"; }

# ── 1. Arrancar n8n ──────────────────────────────────────────────────────────
log "Arrancando n8n..."
n8n start &
N8N_PID=$!

# ── 2. Esperar a que n8n esté listo ─────────────────────────────────────────
log "Esperando a que n8n esté listo..."
until wget -qO- http://localhost:5678/healthz > /dev/null 2>&1; do
  sleep 2
done
log "n8n listo."

# ── 3. Importar workflows (reintentar hasta que exista un owner) ─────────────
# En el primer arranque n8n necesita que el usuario cree su cuenta en la UI
# antes de poder importar. El bucle reintenta cada 10s indefinidamente.
log "Importando workflows (esperando a que se complete el setup de n8n)..."
until n8n import:workflow --separate --input=/workflows > /tmp/import.log 2>&1; do
  log "Import pendiente (¿falta crear la cuenta en http://localhost:5678?). Reintentando en 10s..."
  cat /tmp/import.log
  sleep 10
done
log "Workflows importados OK."

# ── 4. Mantener el proceso vivo ─────────────────────────────────────────────
wait $N8N_PID
