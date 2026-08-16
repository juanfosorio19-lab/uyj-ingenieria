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

Python + FastAPI · Postgres (Supabase/Docker) · n8n (orquestación) · Alpaca paper (fase 0–4) · adapter de broker intercambiable (Alpaca/eToro/IBKR/manual) · Claude API (análisis) · Telegram (alertas y aprobaciones).

## Estado

**Fase 0 — Reset y esqueleto.** Este commit es el punto de partida: repo limpio + plan.
