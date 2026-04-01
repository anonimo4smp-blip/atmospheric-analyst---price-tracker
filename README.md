# Atmospheric Analyst — Price Tracker

Monitoriza precios de productos en **Amazon ES** y **PCComponentes** y recibe alertas por email cuando bajan de tu precio objetivo.

**Demo del frontend:** [atmospheric-analyst.vercel.app](https://atmospheric-analyst.vercel.app) *(requiere backend propio para funcionar)*

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React 19 + Vite + Tailwind v4 |
| Backend | FastAPI (Python) |
| Base de datos | PostgreSQL 16 |
| Automatización | n8n |
| Scrapers | Playwright (Amazon ES, PCComponentes) |
| Despliegue | Docker Compose |

---

## Opción 1 — Solo el frontend (Vercel)

El frontend se puede desplegar en Vercel de forma independiente. Sin backend solo verás la pantalla de login; para el funcionamiento completo necesitas el backend accesible públicamente.

### Pasos

1. Importa este repositorio en [vercel.com](https://vercel.com)
2. Vercel detectará el `vercel.json` automáticamente — no necesitas cambiar nada en el dashboard
3. Añade la variable de entorno en **Settings → Environment Variables**:
   ```
   VITE_API_BASE_URL = https://tu-backend.ejemplo.com
   ```
4. Despliega

---

## Opción 2 — Stack completo con Docker Compose

### Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecución

### Instalación

```bash
# 1. Clona el repositorio
git clone https://github.com/tu-usuario/atmospheric-analyst---price-tracker.git
cd atmospheric-analyst---price-tracker

# 2. Copia el fichero de variables de entorno y edítalo
cp .env.example .env
```

Abre `.env` y cambia como mínimo:

| Variable | Descripción |
|---|---|
| `AUTH_JWT_SECRET` | Secreto para firmar los JWT (cualquier string largo) |
| `INTERNAL_API_KEY` | Clave para comunicación interna backend↔n8n |
| `ALERT_EMAIL` | Email donde recibirás las alertas de precio |
| `AUTH_EMAIL_SMTP_*` | Credenciales SMTP para el envío de emails |

```bash
# 3. Arranca todos los servicios
docker compose up -d

# 4. Abre el navegador
# Frontend:  http://localhost:5174
# Backend:   http://localhost:8001/docs
# n8n:       http://localhost:5679
```

### Comandos útiles

```bash
docker compose logs -f backend     # Ver logs del backend
docker compose restart backend     # Reiniciar el backend
docker compose down                # Parar todo
docker compose up -d --build       # Reconstruir y arrancar
```

---

## Variables de entorno

| Fichero | Propósito |
|---|---|
| `.env` | Configuración de todos los servicios (copia de `.env.example`) |
| `front/.env` | Solo necesario para desarrollo local del frontend fuera de Docker |

---

## Tiendas soportadas

- `amazon.es`
- `pccomponentes.com`

Para añadir una tienda nueva, implementa `ScraperBase` y regístrala en `backend/app/services/price_check_service.py`.
