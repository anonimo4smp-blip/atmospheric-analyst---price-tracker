# Configuración de n8n

## Arranque completo en 2 pasos

### 1. Configura tu `.env`

```env
# Clave de encriptación de n8n
N8N_ENCRYPTION_KEY=pon-aqui-una-clave-larga-y-aleatoria

# SMTP para alertas de precio (usado por el BACKEND, no por n8n directamente)
AUTH_EMAIL_SMTP_HOST=smtp.gmail.com
AUTH_EMAIL_SMTP_PORT=587
AUTH_EMAIL_SMTP_USER=tu@gmail.com
AUTH_EMAIL_SMTP_PASS=tu-app-password     # ver nota Gmail abajo
AUTH_EMAIL_SMTP_SENDER=tu@gmail.com
AUTH_EMAIL_SEND_ENABLED=true

# Email donde llegan las alertas
ALERT_EMAIL=destino@example.com

# Clave interna backend ↔ n8n
INTERNAL_API_KEY=una-clave-segura-larga
```

### 2. Levanta el stack

```bash
docker compose up -d
```

Los workflows se importan automáticamente. n8n estará en http://localhost:5679.

---

## Cómo funciona el envío de email

El nodo **Enviar Email** del workflow NO usa SMTP propio de n8n. En su lugar llama a:

```
POST /internal/alerts/{id}/send-email
```

El backend envía el email usando su propia configuración SMTP (`AUTH_EMAIL_SMTP_*`),
marca la alerta como enviada y devuelve `{"status": "sent"}`.

Esto significa que **n8n no necesita credenciales SMTP** — todo se configura en `.env`.

---

## Paso manual final — Activar los workflows

Una sola vez, tras el primer arranque:

1. Abre http://localhost:5679 (crea tu cuenta de n8n si te lo pide)
2. Ve a **price-check-daily-alerts** → activa el toggle
3. Ve a **price-check-manual-webhook** → actívalo también

---

## Gmail — App Password

1. Ve a https://myaccount.google.com/apppasswords
2. Crea una App Password para "Mail"
3. Úsala como `AUTH_EMAIL_SMTP_PASS` en tu `.env`

---

## Flujo del workflow diario

```
Cron 00:00
  └→ POST /internal/jobs/check-prices        (scrapea y genera alertas)
       └→ GET /internal/alerts/pending
            └→ por cada alerta:
                 └→ POST /internal/alerts/{id}/send-email
                      (backend envía email SMTP y marca como enviada)
```

## Test manual

```bash
curl -X POST http://localhost:5679/webhook/price-check-manual
```
