# Plan por fases — cada fase termina con algo que puedes ver

Principios que gobiernan el plan:

1. **Cada fase produce algo visible.** No hay fases de "plomería invisible": si al final de la fase no puedes abrir algo y verlo funcionar, la fase está mal cortada.
2. **Autonomía creciente, no autonomía prometida.** Cada fase automatiza algo que en la anterior era manual. La lista de tareas manuales se publica en cada fase y solo puede achicarse.
3. **La IA propone, las reglas ejecutan.** El LLM nunca tiene credenciales ni herramienta de ejecución. Devuelve JSON; un Risk Engine determinista valida contra límites duros y un Order Service idempotente ejecuta. Las 5 reglas de salida (stop duro, invalidador de tesis, horizonte, concentración, mantener) no consultan a la IA jamás.
4. **Criterios de salida cuantitativos.** No se pasa de fase "porque ya toca". Si no se cumplen, se ajusta la estrategia, no el criterio.

**Horario de operación:** el agente solo trabaja cuando el mercado trabaja. NYSE opera lunes a viernes 9:30–16:00 hora de Nueva York (≈10:30–17:00 o 11:30–18:00 hora de Chile según horario de verano de cada país). Los crons de n8n se acotan a eso: monitoreo cada 15 min **solo con mercado abierto**, análisis LLM una vez **después del cierre** (vía Batch API, sin apuro), y nada corre de noche ni fines de semana ni feriados de mercado (calendario de feriados NYSE en la config). El VPS queda encendido 24/7 igual (cuesta lo mismo), pero el sistema consume datos y LLM solo en ventana de mercado.

Lo manual que **nunca** se va a poder eliminar (y está bien que así sea): abrir cuenta de broker (KYC), fondear/retirar capital, firmar el F22 y la DJ 1929 ante el SII, y aprobar cambios a los parámetros de riesgo.

---

## Fase 0 — Reset y esqueleto vivo (semana 1)

**Objetivo:** repo limpio, entorno reproducible, y el primer circuito completo aunque sea trivial.

- Docker Compose: Postgres + FastAPI + n8n levantan con un comando.
- Esquema de base de datos completo desde el día 1 (incluye `tax_lots`, `executions`, `reconciliations`, `theses`, `kill_switch_events` — cuestan lo mismo ahora que después, y después es tarde).
- Interfaz `BrokerAdapter` + `PaperAdapter` (la decisión de arquitectura más importante: cambiar de broker será una línea de config).
- Bot de Telegram conectado.
- GitHub Actions corre tests en cada push.

**Lo que VES al terminar:** le escribes `/status` al bot en Telegram y responde con posiciones y caja simuladas; le escribes `/buy AAPL 100` y la posición aparece y persiste. CI en verde en el repo.

**Manual en esta fase:** todo se lanza a mano. Es la última fase donde eso es verdad.

**Criterio de salida:** test automatizado compra/vende en paper y las posiciones sobreviven un reinicio del contenedor.

---

## Fase 1 — Ojos: datos que llegan solos (semanas 2–3)

**Objetivo:** el sistema se alimenta sin que nadie lo toque.

- Ingesta diaria automática (n8n cron) de OHLCV para ~50 tickers, 3 años de historia inicial.
- Universo point-in-time (constituyentes históricos, no la lista de hoy — sin esto el backtest de la fase 2 miente).
- Ingesta de fundamentales desde SEC EDGAR con **fecha de publicación** real.
- Tabla `fx_rates` con dólar observado diario (insumo tributario).

**Lo que VES al terminar:** todas las mañanas, sin tocar nada, llega un mensaje a Telegram: resumen del mercado, top movers de tu universo, y estado de la ingesta (cuántos tickers, huecos detectados). Si un día no llega, eso también es información.

**Manual eliminado respecto a fase 0:** ya no se lanza nada a mano; el sistema vive solo en cron.

**Criterio de salida:** 7 días corridos de ingesta sin intervención y sin huecos silenciosos.

---

## Fase 2 — Cerebro mecánico: scoring y backtest honesto (semanas 4–6)

**Objetivo:** la parte del sistema que SÍ se puede validar contra el pasado, validada.

- Motor de scoring mecánico (momentum, valoración, calidad) reproducible para cualquier fecha histórica.
- Backtest walk-forward con vectorbt/backtesting.py: costos modelados (comisión + spread + slippage + FX), sin look-ahead, sin survivorship.
- El componente LLM queda explícitamente FUERA del backtest (un LLM no puede backtestearse honestamente sobre noticias que ya conoce; se valida hacia adelante en la fase 4).

**Lo que VES al terminar:** un reporte HTML (generado automático cada semana) con curvas de equity de tu estrategia vs. comprar y mantener SPY, en 4 ventanas walk-forward independientes, después de costos.

**Criterio de salida:** el componente mecánico bate a SPY después de costos en **≥3 de 4 ventanas**. Si no lo logra, se itera la estrategia aquí — es la fase más barata para fallar.

---

## Fase 3 — Analista IA + motor de riesgo (semanas 7–8)

**Objetivo:** incorporar el LLM de forma segura y barata, y el guardián determinista que lo contiene.

- LLM Analyst (Claude Haiku 4.5 vía Batch API para el análisis diario; Sonnet 5 solo para tesis de entrada): recibe un dict allowlist (precios, posiciones, noticias — nada más), devuelve JSON validado con Pydantic.
- Cada propuesta de compra incluye **tesis falsable con invalidadores** medibles.
- Risk Engine: límites de concentración, stop duro −20%, límite de exposición — reglas duras fuera del alcance del modelo.
- Order Service idempotente (`client_order_id` determinista: un reintento de n8n jamás compra dos veces).
- Filtro de redacción de secretos en logs; `prompt_hash` y `model_version` en cada decisión (auditable).

**Lo que VES al terminar:** cada mañana llega a Telegram la propuesta del día: "COMPRAR NVDA 3%, tesis: X, invalidadores: Y, veredicto del Risk Engine: aprobada/rechazada y por qué". Todavía no ejecuta — tú ves cómo piensa antes de soltarle la mano.

**Tests de salida (los tres son bloqueantes):** (1) un secreto inyectado en config NO aparece en ningún prompt; (2) doble llamada al Order Service = una sola orden; (3) JSON malformado del LLM → rechazado y registrado, nunca ejecutado.

---

## Fase 4 — Piloto automático en paper (semanas 9–17: 60 días de mercado)

**Objetivo:** el sistema completo operando solo, con dinero de mentira, sin que lo toques.

- Alpaca paper trading: el ciclo completo decide → valida → **ejecuta** → reconcilia, sin humano.
- Monitoreo cada 15 min en mercado abierto: stops y ventas defensivas automáticas.
- Reconciliación contra el broker antes de cada decisión (divergencia → HALT + alerta).
- Dead man's switch (sin heartbeat 15 min → órdenes deshabilitadas solas) y kill switch por Telegram.
- Se despliega a un VPS: deja de depender de tu computador.
- **Disciplina: 60 días sin tocar la estrategia.** Es la parte más difícil del proyecto.

**Lo que VES al terminar (y durante):** un dashboard web con curva de equity, posiciones, cada decisión con su tesis y su resultado, y calidad de ejecución. Más el resumen diario en Telegram. Ves a tu agente operar solo todos los días.

**Manual eliminado:** ejecución y vigilancia. Tu rol queda reducido a espectador con botón rojo.

**Criterios de salida (todos, sin renegociar):** ≥40 decisiones registradas · max drawdown <15% · Sharpe >0,5 · cero discrepancias de reconciliación sin explicar · cero órdenes duplicadas · kill switch probado ≥3 veces con éxito.

---

## Fase 5 — Dinero real de matrícula (semanas 18–30)

**Objetivo:** medir lo que el paper no puede: slippage real, latencia real, y tu estómago. USD 200–500. **El objetivo NO es ganar plata.**

- Broker live según lo que respondieron Alpaca/eToro/IBKR (el adapter hace el cambio trivial). Verificaciones a correr en paralelo desde la fase 0 — son la única dependencia externa lenta:
  - [ ] Alpaca: ¿cuenta live para residente chileno?
  - [ ] eToro: ¿API keys desde Chile? ¿acciones reales o CFDs?
  - [ ] IBKR: iniciar solicitud de cuenta cash ya (demora días)
  - [ ] Contador: compensación de pérdidas extranjeras + tratamiento CFDs
- Tax ledger FIFO activo desde la **primera** orden real: cada venta genera su lote tributario con FX del día.
- Autonomía calibrada: ventas defensivas y rebalanceo 100% automáticos; posiciones nuevas requieren un toque en un botón inline de Telegram (aprobar/rechazar en 5 segundos). Ese botón es temporal y medible: cuando llevas N semanas aprobando todo sin excepción, se elimina.
- Límite que ningún bug puede saltarse: en la cuenta del broker solo vive el capital autorizado.

**Lo que VES al terminar:** tu primera orden real ejecutada por el agente, y un reporte de calidad de ejecución: precio de decisión vs. precio de fill, slippage acumulado, tasa de fallos.

**Criterios de salida:** slippage promedio <0,3% por operación · fallos de ejecución <1% · tú durmiendo tranquilo (en serio: si revisas el portafolio >3 veces al día, no se avanza).

---

## Fase 6 — Autonomía supervisada con capital significativo (semana 30+)

**Objetivo:** el estado final realista. Solo si las fases anteriores pasaron **con sus criterios originales**.

- Capital del orden de USD 5.000+ (donde los costos fijos caen bajo 0,5% anual).
- Automático sin preguntar: ventas defensivas, rebalanceo dentro de límites, posiciones nuevas dentro de los parámetros del Risk Engine, reportes, reconciliación, y el borrador de la DJ 1929 cada enero.
- Requiere tu aprobación (por diseño, para siempre): cambios de parámetros de riesgo, operaciones >5% del portafolio, aportes/retiros de capital.
- Evaluación mensual automática del sistema con reporte: ¿los pesos siguen sirviendo? ¿el slippage se comió el edge?

**Lo que VES:** un reporte mensual que llega solo, y en enero un borrador de DJ 1929 listo para tu contador. Tu participación rutinaria: leer un mensaje al día y uno al mes.

**Señales automáticas de parada** (el sistema se detiene solo y te avisa): drawdown mensual >10% · divergencia de reconciliación · cualquier intento de orden fuera de límites.

---

## Resumen: la trayectoria de autonomía

| Fase | Decide | Ejecuta | Vigila | Tu rol |
|---|---|---|---|---|
| 0 | tú | tú (simulado) | tú | constructor |
| 1 | — | — | sistema (datos) | constructor |
| 2 | backtest | — | sistema | analista |
| 3 | sistema (propone) | nadie aún | sistema | revisor diario |
| 4 | sistema | sistema (paper) | sistema | espectador con botón rojo |
| 5 | sistema | sistema (real, con un botón temporal) | sistema | supervisor decreciente |
| 6 | sistema | sistema (dentro de límites) | sistema | 1 mensaje/día, 1 reporte/mes |
