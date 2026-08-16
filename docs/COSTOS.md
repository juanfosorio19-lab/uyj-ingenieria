# ¿Cuánto cuesta este agente?

Respuesta corta: **casi nada mientras validas (USD 0–10/mes), y USD 15–45/mes cuando opere con dinero real.** El costo dominante no es la infraestructura: son los impuestos y el spread cambiario cuando ya operas de verdad, y esos escalan con el capital, no con el software.

Todo en USD. Precios verificados a agosto 2026.

## 1. Costo por componente

### LLM (análisis diario de noticias/tesis)

Carga estimada: 20 empresas/día, ~6.000 tokens de entrada y ~700 de salida por empresa, más una síntesis diaria. ≈ **4M tokens entrada + 0,5M salida al mes**.

| Modelo | Precio (in/out por MTok) | Costo mensual directo | Con Batch API (−50%) |
|---|---|---|---|
| Claude Haiku 4.5 | $1 / $5 | ~$6,5 | **~$3,3** |
| Claude Sonnet 5 | $3 / $15 (intro $2/$10 hasta 31-08-2026) | ~$19 (intro ~$12,5) | ~$9,5 (intro ~$6,3) |

El análisis diario post-cierre no necesita respuesta inmediata → **Batch API siempre** (procesa en <1 hora, mitad de precio). Recomendación: Haiku 4.5 para el scoring/sentimiento rutinario y Sonnet 5 solo para la tesis de entrada de una posición nueva (pocas por semana). **Presupuesto realista: USD 3–8/mes.**

### Datos de mercado

| Fuente | Costo | Cuándo |
|---|---|---|
| yfinance | $0 | Desarrollo y backtest |
| Alpaca Market Data (IEX, tiempo real básico) | $0 | Paper trading y producción inicial — viene con la cuenta |
| SEC EDGAR (fundamentales con fecha de publicación) | $0 | Siempre — oficial y gratis |
| EODHD o Financial Modeling Prep | $20–30/mes | Solo si en producción necesitas datos EOD de mejor calidad. Postergable. |

### Infraestructura

| Componente | Costo | Nota |
|---|---|---|
| Tu propia máquina + Docker | $0 | Fases 0–4 completas |
| VPS (Hetzner CX22 / DigitalOcean básico) | $5–12/mes | Necesario recién en fase 4–5, cuando el sistema debe correr 24/7 sin depender de tu PC |
| Postgres | $0 | Supabase free tier o Postgres en el mismo Docker/VPS |
| n8n self-hosted | $0 | Corre en el mismo Docker |
| Telegram Bot API | $0 | |
| Broker: Alpaca paper | $0 | Ilimitado, sin aprobación de cuenta |
| Broker: Alpaca live / IBKR cash | $0 mensual | IBKR sin mínimo en cuenta cash; comisiones por operación ~$0,005/acción |

### Costos de operar con dinero real (no son infraestructura, pero son los que importan)

| Concepto | Magnitud |
|---|---|
| Conversión CLP→USD ida y vuelta | 0,5–1%+ del capital, cada vez |
| Comisiones + spread + slippage | ~0,1–0,4% por operación (el sistema lo mide en la tabla `executions`) |
| Impuesto Global Complementario (Chile) sobre ganancias realizadas | 0–40% marginal — la razón para diseñar con baja rotación |
| Contador (consulta única, arts. 41 A/B y DJ 1929) | ~$50–150 una vez |

## 2. Costo total por fase

| Fase | Qué corre | Costo mensual |
|---|---|---|
| 0–2 (esqueleto, datos, backtest) | Tu máquina, tiers gratis, LLM casi sin uso | **~$0–3** |
| 3–4 (IA + paper trading 24/7) | LLM diario en batch + VPS opcional al final | **~$3–15** |
| 5 (dinero real chico, USD 200–500) | VPS + LLM + datos gratis | **~$10–20** |
| 6 (capital significativo) | VPS + LLM + datos pagados opcionales | **~$15–45** |

## 3. La cuenta que hay que mirar de frente

Con **USD 300** de capital, USD 20/mes de costos fijos = **80% anual solo para empatar**. Ninguna estrategia sostiene eso. Por eso el plan trata las fases 0–4 como costo ≈ 0 (validación), la fase 5 como **matrícula de un curso** (el objetivo es medir slippage, latencia y tu psicología — no ganar plata), y recién con **USD 5.000–10.000** los costos fijos caen bajo el 0,5% anual y el retorno puede ser el objetivo.

## 4. Presupuesto total del proyecto hasta autonomía

- **Meses 1–4 (fases 0–4):** ~$10–40 acumulado total.
- **Meses 5–7 (fase 5):** ~$30–60 acumulado + capital de matrícula USD 200–500 (que no es gasto: sigue siendo tuyo, con riesgo de mercado).
- **Único costo "grande" evitado:** no se compra motor de backtest, ni plataforma, ni datos premium. Todo el valor está en el código del repo.
