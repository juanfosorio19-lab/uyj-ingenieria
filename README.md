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

**Sin Docker** (desarrollo local, usa SQLite en `./data/agent.db` y lee el `.env` automáticamente):

Windows (PowerShell):

```powershell
winget install -e --id Python.Python.3.12   # si no tienes Python; luego reabre la terminal
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest               # correr los tests
.venv\Scripts\python -m uvicorn app.main:app # API en localhost:8000
.venv\Scripts\python -m app.telegram_bot     # bot (en otra terminal)
```

Mac/Linux:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                                   # correr los tests
.venv/bin/uvicorn app.main:app --reload            # API con SQLite local
.venv/bin/python -m app.telegram_bot               # bot
```

### Fase 1: datos que llegan solos

```powershell
.venv\Scripts\python -m app.jobs ingest    # backfill 3 años, 51 símbolos (primera vez: minutos)
.venv\Scripts\python -m app.jobs fx        # dólar observado del día (mindicador.cl)
.venv\Scripts\python -m app.jobs report    # arma el resumen y lo manda a tu Telegram
.venv\Scripts\python -m app.jobs daily     # los tres en orden
.venv\Scripts\python -m app.scheduler      # queda corriendo: días hábiles 16:45 NY, solo
```

(En Mac/Linux: `.venv/bin/python -m app.jobs daily`.) Con Docker, el servicio `scheduler` del compose hace esto solo.

### Fase 2: backtest walk-forward

```powershell
.venv\Scripts\python -m app.jobs backtest  # corre el backtest y manda el HTML a tu Telegram
```

Genera `reports\backtest.html` (curvas de equity vs SPY, 4 ventanas, veredicto) y lo envía al chat.

### Fase 3: analista IA + motor de riesgo

```powershell
.venv\Scripts\python -m app.jobs propose   # tesis del día + veredicto del Risk Engine a Telegram
```

Con `ANTHROPIC_API_KEY` en el `.env`, la tesis la escribe Claude; sin key, un analista de reglas (momentum) — el circuito es el mismo. La propuesta también sale sola dentro del ciclo `daily`.

## Estado

**Fase 0 cerrada** ✅ — validada en el PC de Juan: API + bot de Telegram respondiendo, kill switch probado.

**Fase 1 en observación** ⏳ — ingesta + FX + reporte diario construidos y funcionando; scheduler activo en el PC. Criterio: **7 días corridos de reportes sin intervención** (corriendo desde el 17-08-2026).

**Fase 2 construida (provisoria)** ⏳ — scoring de momentum 6m−1m con hipótesis declarada, backtest walk-forward sin look-ahead con costos explícitos (0,2% por lado), 4 ventanas vs SPY, reporte HTML con veredicto enviado a Telegram. **Provisoria porque falta**: universo con constituyentes históricos (hoy hay survivorship bias) y factores fundamentales con SEC EDGAR point-in-time. El criterio de salida (≥3 de 4 ventanas batiendo a SPY después de costos) solo se evalúa en firme con eso cargado.

**Fase 3 cerrada** ✅ — analista con tesis falsables (Claude vía `ANTHROPIC_API_KEY`, o analista de reglas sin key), prompt construido por allowlist (los secretos no pueden llegar al modelo — con test que lo garantiza), validación Pydantic (JSON inválido o posición >10% → rechazado y auditado, jamás usado), auditoría completa en `ai_decisions` (prompt_hash + model_version), y Risk Engine determinista de entrada. Validada en producción: propuesta con IA real llegando a Telegram.

**Fase 4a construida** ⏳ — ejecución real en Alpaca paper: `AlpacaAdapter` (REST, sin SDK) con idempotencia de mercado (el broker rechaza `client_order_id` repetidos y el agente lo maneja sin duplicar), kill switch respetado antes de tocar la red, **reconciliación broker vs. local antes de cada decisión** (divergencia → HALT automático + alerta), espejo local sincronizado desde el broker, y ciclo `trade` = reconciliar → analizar → riesgo → ejecutar → sincronizar. Se activa con `BROKER=alpaca` y `EXECUTION_ENABLED=true` en el `.env`. 40 tests en verde. Pendiente de la fase 4: ventas defensivas cada 15 min, dead man's switch y dashboard web.
