# Agente de Trading Autónomo

Sistema automatizado de inversión en acciones USA: datos de mercado → scoring mecánico → análisis con IA → motor de riesgo determinista → ejecución vía broker API, con notificaciones por Telegram y registro tributario (Chile) desde el día uno.

> ⚠️ Este repo era antes el sitio de UYJ Ingeniería. Se limpió por completo para este proyecto. Para renombrarlo: **Settings → General → Repository name** (GitHub redirige la URL vieja automáticamente, no se pierde nada).

## Documentos

| Documento | Qué contiene |
|---|---|
| [docs/COSTOS.md](docs/COSTOS.md) | Cuánto cuesta operar el agente, por fase, con números reales |
| [docs/PLAN-FASES.md](docs/PLAN-FASES.md) | Plan de ejecución en 7 fases, cada una con algo visible al terminar |
| [docs/IMPUESTOS-CHILE.md](docs/IMPUESTOS-CHILE.md) | Simulación de impuestos en Chile: tramos, escenarios y calendario |
| [docs/plan-original.md](docs/plan-original.md) | El plan de ingeniería original (análisis de bloqueadores, arquitectura, seguridad) |

## Resumen en 30 segundos

- **Costo de operación:** USD 0–10/mes mientras el sistema corre en paper trading (fases 0–4); USD 15–45/mes en producción con dinero real. El detalle está en [COSTOS.md](docs/COSTOS.md).
- **Fases:** 7 fases, de ~1 a ~12 semanas cada una. Cada fase termina con algo que puedes **ver funcionando** (un bot que responde, un reporte diario en Telegram, un backtest HTML, un dashboard, una orden real ejecutada).
- **Autonomía:** el objetivo es que el sistema decida y ejecute solo dentro de límites duros. Lo manual se reduce fase a fase hasta quedar en 4 cosas que ninguna automatización puede hacer por ti: abrir la cuenta del broker (KYC), fondearla, firmar la declaración de impuestos y aprobar cambios a las reglas de riesgo.
- **Principio de seguridad:** la IA nunca toca credenciales ni ejecuta órdenes. Propone en JSON; un motor de riesgo determinista valida y ejecuta. El kill switch y los límites viven fuera del alcance del modelo.

## Stack

Python + FastAPI · Postgres (Docker) · n8n (orquestación) · Telegram (alertas y ejecución guiada) · Claude API (análisis) · adapter de broker intercambiable.

**Ruta de brokers decidida:** Alpaca paper para pruebas (fases 0–4) → **Racional con ejecución manual guiada por Telegram** en producción (fase 5) → autonomía cambiando el adapter a un broker con API, IBKR o Alpaca live (fase 6).

## Cómo correr (Fase 0)

```bash
cp .env.example .env        # opcional: agrega tu token de Telegram
docker compose up --build   # levanta Postgres + API + n8n (+ bot si hay token)

curl localhost:8000/status  # caja, posiciones, kill switch, mercado abierto/cerrado
```

API en `localhost:8000` (docs interactivas en `/docs`), n8n en `localhost:5678`.

**Bot de Telegram:** crea un bot con [@BotFather](https://t.me/BotFather), pega el token en `.env` (`TELEGRAM_BOT_TOKEN=...`) y reinicia el compose. Comandos: `/status`, `/buy AAPL 10 230.50`, `/sell AAPL 5`, `/kill`, `/resume`. Con `TELEGRAM_CHAT_ID` definido, el bot ignora a cualquier otra persona.

**Sin Docker** (desarrollo local):

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                                   # correr los tests
.venv/bin/uvicorn app.main:app --reload            # API con SQLite local
.venv/bin/python -m app.telegram_bot               # bot
```

## Estado

**Fase 0 construida** ✅ — esqueleto vivo: Postgres + FastAPI + bot de Telegram + `PaperAdapter` con idempotencia, kill switch y lotes tributarios FIFO desde la primera compra simulada. 10 tests en verde + CI en GitHub Actions.

Pendiente para cerrar la fase (lo haces tú, ~10 min): correr `docker compose up` en tu máquina y probar `/status` y `/buy` desde tu Telegram. Siguiente: **Fase 1 — datos que llegan solos**.
