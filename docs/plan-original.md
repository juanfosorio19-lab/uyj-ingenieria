# Agente de inversión automatizado — Plan de ejecución

**Autor:** Juan Fabián Osorio
**Fecha:** 16 de agosto de 2026
**Estado:** Diseño — pendiente de 4 verificaciones bloqueantes

> Nota: esto es un plan de ingeniería, no asesoría financiera ni tributaria. No soy asesor de inversiones ni contador. Las cifras y reglas de riesgo son ejemplos de diseño, no recomendaciones.

---

## 0. Veredicto en una página

Tu idea es construible, y tienes razón en lo central: **no necesitas entregarle credenciales a ninguna IA para que esto funcione.** La arquitectura correcta hace que el modelo nunca vea un secreto, ni siquiera "en un archivo". Esa parte la resolvemos limpiamente (sección 6).

El documento de ChatGPT tiene una arquitectura razonable —separación IA/Risk Engine, fases, kill switch— y esas partes las conservo. Pero tiene **tres errores que te costarían meses** si los sigues tal cual:

| # | Lo que dice ChatGPT | Realidad verificada | Impacto |
|---|---|---|---|
| 1 | "Fase 2 — conectar Racional vía DriveWealth API" | DriveWealth es **B2B2C puro**. El contrato de API es con Vector Capital/Racional, no contigo. No existe credencial de usuario final. | La Fase 2 completa es inejecutable como está escrita |
| 2 | No menciona impuestos | En Chile **cada venta con ganancia** de acción extranjera va a Global Complementario (0–40%), costo FIFO, DJ 1929 obligatoria aunque pierdas | Cambia el diseño de la estrategia y agrega un módulo obligatorio |
| 3 | "Backtesting con LLM 2019–2026" | **No se puede backtestear honestamente un LLM sobre noticias históricas.** El modelo ya sabe qué pasó. | El backtest daría resultados espectaculares y completamente falsos |

Y una omisión de escala: con USD 100–300 de capital, **la infraestructura cuesta más que cualquier retorno plausible**. Eso no invalida el proyecto, pero redefine qué es "éxito" en la fase de validación.

---

## 1. Bloqueador #1 — Racional no tiene puerta de entrada

### Qué encontré

- Racional Stocks efectivamente usa **DriveWealth** como broker en EE.UU., vía **Vector Capital Corredores de Bolsa** como intermediario regulado CMF.
- DriveWealth se define como plataforma **B2B / Brokerage-as-a-Service**: provee API a fintechs, bancos y broker-dealers para que *ellos* la incrusten en sus apps. El cliente de la API es el partner, no el inversionista.
- La documentación de DriveWealth habla de "Partners" y "Partners' clients". Los flujos de onboarding son para que el partner cree usuarios, no para que un usuario se autogestione.
- En el board público de feedback de Racional hay una solicitud de **API pública** con años de antigüedad y sin respuesta, con múltiples usuarios pidiendo exactamente lo que tú quieres ("necesito tradear con Agentes IA").

**Conclusión:** no hay ruta técnica legítima de tu cuenta Racional a la API de DriveWealth. Esto no es un "hay que verificarlo", es estructural al modelo de negocio.

### Las 5 salidas (ordenadas por relación valor/riesgo)

Me pediste no abandonar y dar alternativas para que tú elijas. Estas son:

---

**RUTA A — Alpaca (paper primero, live después)**
- API de trading completa, paper trading gratuito e ilimitado, documentación excelente, ecosistema Python maduro.
- Acepta no-residentes de EE.UU. con verificación KYC internacional, sin depósito mínimo. **Chile no está confirmado en la lista pública** — hay que escribir a `support@alpaca.markets` y preguntar explícitamente. Alpaca sí opera en Chile como infraestructura B2B (potencia a *trii*), pero eso es distinto del onboarding retail directo.
- **Mejor opción para construir.** Aunque el live no funcione en Chile, el paper trading no requiere aprobación de cuenta y te da 100% del valor de la Fase 0–1.

**RUTA B — eToro API pública** ⭐ *lo más nuevo y probablemente lo que ChatGPT no sabía*
- eToro lanzó APIs públicas en octubre 2025 y las expandió en abril 2026 con Builders Portal y App Store.
- Hoy expone **179+ endpoints REST**, WebSocket en tiempo real, trading algorítmico programático, gestión de portafolio y P&L, watchlists. Incluso publican MCP y Agent Skills.
- Autenticación por **API key generada desde la configuración de tu propia cuenta** (`x-api-key` + `x-user-key`), con permisos read/write separados y claves demo vs. real.
- eToro opera en ~75 países con cuentas fondeadas. **Verificar disponibilidad Chile y si te ofrecen acciones reales o CFDs** — esto es crítico: los CFDs tienen tratamiento tributario y de riesgo totalmente distinto.
- Riesgo: es una plataforma con historial de comisiones de retiro y spread de conversión de divisa.

**RUTA C — Interactive Brokers**
- Acepta residentes chilenos. Cuenta *cash* sin mínimo; cuenta *margin* desde USD 2.000.
- Dos APIs: **Client Portal Web API** (REST, más simple) y **TWS API** (requiere gateway corriendo). Ambas maduras.
- Comisiones desde ~USD 0,005/acción. Sin fraccionamiento tan flexible como Racional para montos micro.
- **La opción más robusta a largo plazo.** Más fricción de onboarding, más papeleo, pero es el broker que usarías si esto funciona.

**RUTA D — Racional como custodia + bot como asesor** ✅ *ejecutable esta semana*
- El bot corre completo: datos, scoring, riesgo, decisión. Pero **no ejecuta**. Te manda a Telegram: "COMPRAR NVDA, 3% del portafolio, razón X, riesgo Y".
- Tú abres la app y ejecutas manualmente en 20 segundos.
- Cero riesgo de ToS, cero riesgo de bug ejecutando órdenes, cero espera de aprobación de cuenta.
- **Recomendación fuerte: haz esto en paralelo a todo lo demás.** Es el 80% del valor con el 5% del riesgo, y valida si las señales sirven antes de invertir en plomería.

**RUTA E — Playwright sobre la app de Racional** ⚠️
- Técnicamente posible. Pero: casi con certeza viola los términos de servicio (riesgo de cierre de cuenta), se rompe con cada deploy de ellos, el MFA lo complica, y —lo peor— el ratio de fallos silenciosos en automatización de UI financiera es inaceptable. Una orden que "creíste" que se envió y no se envió es peor que ninguna orden.
- **Último recurso. No la recomiendo.**

### Detalle que casi nadie considera

Las órdenes fraccionarias en DriveWealth se ejecutan típicamente **en ventanas agrupadas**, no de forma continua. Es decir: aunque tuvieras API en Racional, tu "decisión de las 10:00" no se ejecuta a las 10:00. Un bot horario sobre fraccionarios es una ficción. Verifícalo con soporte de Racional si insistes en esa ruta.

---

## 2. Bloqueador #2 — El módulo tributario que falta

Esto no aparece en el plan de ChatGPT y es **obligatorio, no opcional**, para un residente tributario chileno.

### Las reglas que te aplican

- Art. 3° LIR: residentes en Chile tributan por rentas de fuente chilena **y extranjera**.
- Ganancias de capital por venta de acciones en bolsas extranjeras: régimen general, **Impuesto Global Complementario**, se suman a tu sueldo y demás rentas. Tramo marginal 0% a 40%.
- **No hay exención por presencia bursátil** para acciones extranjeras — la exención del 107 LIR es para el mercado local.
- Costo de adquisición: **FIFO** (así lo aplica Racional en sus reportes).
- **DJ 1929** ("Operaciones en el exterior"): obligatoria **aunque hayas perdido plata**, aunque no hayas vendido nada. Vence 30 de junio por las operaciones del año anterior.
- **Formulario 22** en abril, consistente con la DJ 1929.
- Todo se convierte a CLP a la fecha de cada operación (renta líquida percibida).
- Vía CRS, el SII recibe información de brokers extranjeros asociada a tu RUT. No declarar es detectable.

### Por qué esto cambia el diseño, no solo el papeleo

Tu bot original haría decisiones horarias. Supón 3 operaciones por semana → **~150 lotes tributarios al año**. Cada uno con fecha, cantidad, precio USD, tipo de cambio observado del día, matching FIFO contra la compra correspondiente.

Nadie hace eso a mano. Necesitas una tabla `tax_lots` desde el día uno.

Y más de fondo: **la rotación se paga en impuestos**. Un buy & hold difiere el impuesto indefinidamente; tu bot lo paga cada vez que realiza una ganancia. Si tu tramo marginal es 30%, tu estrategia necesita batir al benchmark **por más de 30% de las ganancias realizadas** solo para empatar después de impuestos. Eso es una desventaja estructural enorme y es un argumento fuerte para diseñar hacia **baja rotación** (semanal/mensual), no alta.

> Sobre compensación de pérdidas de fuente extranjera contra ganancias del mismo año: las reglas de los arts. 41 A/41 B no son triviales. Consúltalo con un contador antes de asumir que puedes netear libremente.

### Requisito de diseño derivado

```
tax_lots
  lot_id, symbol, open_date, open_qty, open_price_usd,
  open_fx_clp, remaining_qty, close_date, close_price_usd,
  close_fx_clp, realized_gain_clp, holding_days, method='FIFO'
```

Con un job que genere, en enero de cada año, el borrador de la DJ 1929 en el formato que pide el SII.

---

## 3. Bloqueador #3 — Tu backtest de IA mentiría

Este es el punto técnico más importante de todo el documento.

ChatGPT propone backtestear la estrategia completa —incluyendo el análisis LLM de noticias— sobre 2019–2026. **Eso es imposible de hacer honestamente.**

El modelo que use para "analizar el sentimiento de esta noticia de NVDA de marzo 2023" fue entrenado con datos posteriores. Ya sabe que NVDA subió. No puedes pedirle que lo olvide. El backtest te va a dar un Sharpe de 3.5 y no significa absolutamente nada.

Esto se llama **contaminación por conocimiento de entrenamiento** y es el error dominante en los proyectos de "trading con LLM" que aparecen en GitHub.

### La solución

Parte el sistema en dos y valídalos por caminos distintos:

**Componente mecánico** (precios, indicadores, fundamentales point-in-time)
→ Sí se puede backtestear. Requiere:
- Universo **point-in-time** (constituyentes del índice en cada fecha histórica), no la lista de hoy → si no, tienes *survivorship bias*
- Fundamentales con **fecha de publicación**, no fecha de período (los resultados del Q1 no estaban disponibles el 31 de marzo)
- Modelo de costos: comisión + spread + slippage + FX
- **Walk-forward**, nunca optimización sobre todo el período

**Componente LLM** (noticias, sentimiento, tesis)
→ **Solo validación hacia adelante.** No hay atajo. Corre en paper trading y mide durante 60–90 días reales. Guarda el hash de los inputs y el timestamp de cada decisión para que la evaluación sea auditable.

### Otros errores que matan backtests

| Error | Cómo se manifiesta | Antídoto |
|---|---|---|
| Look-ahead | Usar el cierre del día para decidir "a las 10 AM" | Toda decisión usa solo datos con timestamp < t |
| Survivorship | Backtestear el S&P 500 actual desde 2010 | Constituyentes históricos |
| Sobreajuste | 15 parámetros, 200 trades | Máx. ~1 parámetro por cada 30 observaciones independientes |
| Costos irreales | Asumir fill al precio medio | Modelar spread + slippage explícito |
| p-hacking | Probar 200 combinaciones, reportar la mejor | Declarar la hipótesis *antes*; corregir por múltiples pruebas |

---

## 4. Bloqueador #4 — La economía del capital pequeño

Números concretos.

| Concepto | Costo mensual |
|---|---|
| VPS pequeño | USD 6–20 |
| API de datos de mercado (tier pago) | USD 0–29 |
| LLM (análisis diario de ~20 empresas) | USD 5–30 |
| **Total** | **USD 11–79** |

Con capital de USD 300, USD 30/mes de infraestructura equivale a **120% anual solo para empatar**. Ninguna estrategia hace eso de forma sostenida.

Sumado a esto:
- **Conversión CLP→USD**: spread de ida y vuelta, típicamente 0,5–1%+
- **Regla PDT (FINRA)**: en cuenta *margin* bajo USD 25.000, máximo 3 day trades en 5 días hábiles rodantes. Si la excedes, te congelan la operatoria.
- **Cuenta cash**: evitas el PDT, pero liquidación T+1. Comprar con fondos no liquidados y vender antes → *good faith violation*.

### Qué hacer con esto

No es motivo para abandonar. Es motivo para **redefinir el objetivo de cada fase**:

- **Fases 0–1 (paper):** infraestructura en tu propia máquina, tiers gratuitos, costo ≈ 0. El objetivo es *evidencia sobre la estrategia*.
- **Fase 3 (dinero real pequeño):** el objetivo **NO es ganar plata**. Es medir tres cosas que el paper trading no puede: slippage real, latencia real, y tu propia tolerancia psicológica a ver el número en rojo. Trata los USD 30/mes como matrícula de un curso, no como gasto operacional.
- **Solo pasas a capital significativo** cuando la Fase 1 dio evidencia estadística. Y "significativo" empieza en el orden de USD 5.000–10.000, donde los costos fijos bajan a <0,5% anual.

Diseña para ≤1 decisión al día y horizonte de tenencia ≥5 días. Resuelve PDT, T+1 y buena parte del problema tributario de una sola vez.

---

## 5. Rediseño: cadencia y regla de decisión

### La cadencia horaria está mal planteada

Pediste "mirar cada 1 hora y decidir si comprar o vender". El problema: **la información que justifica una decisión no cambia cada hora.** Fundamentales cambian trimestralmente. Noticias, diariamente. Solo el precio cambia continuamente — y decidir solo por precio a escala horaria es trading técnico de corto plazo, que es un juego distinto (y mucho más difícil) al que describe el resto de tu idea.

**Separación correcta:**

| Frecuencia | Qué hace | Puede ejecutar |
|---|---|---|
| **15 min (mercado abierto)** | Monitoreo: precios, stops, límites de riesgo, circuit breakers | Sí — solo **ventas defensivas** (stop-loss) |
| **1× al día, post-cierre** | Noticias, SEC, fundamentales, sentimiento, rescoring, propuesta de nueva empresa | Propone; ejecuta al día siguiente en la apertura |
| **1× semana** | Rebalanceo, métricas, revisión de tesis abiertas | Sí, con aprobación |
| **1× mes** | Evaluación del sistema: ¿los pesos siguen sirviendo? | No — requiere tu aprobación explícita |

Esto conserva tu intención (vigilancia continua + análisis diario + propuesta diaria) pero pone cada decisión en la escala de tiempo donde su información existe.

### "Si voy ganando vendo / si voy perdiendo compro" — hay que reemplazarla

ChatGPT tiene razón en que promediar a la baja es martingala. Pero su alternativa ("¿cambió la tesis?") es demasiado vaga para codificarla. Necesitas reglas explícitas:

**Cuando compras, el sistema escribe una tesis falsable:**

```json
{
  "symbol": "NVDA",
  "entry_date": "2026-08-16",
  "thesis": "Crecimiento de datacenter sostenido",
  "invalidators": [
    {"metric": "revenue_growth_yoy", "op": "<", "value": 0.15},
    {"metric": "guidance_revision", "op": "==", "value": "down"},
    {"metric": "price_vs_entry", "op": "<", "value": -0.20}
  ],
  "target_horizon_days": 90,
  "max_position_pct": 0.10
}
```

**Reglas de salida, en orden de precedencia:**

1. **Stop duro** (−20% desde entrada) → vender. Sin excepción, sin consultar a la IA.
2. **Invalidador de tesis** → vender.
3. **Horizonte cumplido sin tesis cumplida** → vender.
4. **Límite de concentración excedido** → recortar al límite.
5. Todo lo demás → mantener.

Fíjate que la IA **no participa en ninguna de las cinco**. La IA se usa para *formar* la tesis y los invalidadores en la entrada. Después, la salida es determinista. Eso elimina la clase completa de fallos donde el modelo racionaliza mantener una posición perdedora.

---

## 6. Seguridad: cómo funciona sin que nadie vea tus claves

Tu intuición es correcta y la implementación es más simple de lo que crees.

### El punto clave

**Yo, en este chat, nunca necesito ninguna credencial tuya.** Ni ahora ni nunca. Yo te ayudo a escribir el código; el código corre en tu máquina con tus secretos.

Y dentro de tu sistema, **el LLM tampoco los ve** — no porque "prometa no leerlos", sino porque físicamente no llegan a su contexto:

```
┌────────────────────────────────────────────────┐
│  TU MÁQUINA / VPS                              │
│                                                │
│  ┌──────────────┐                              │
│  │ .env / Vault │  ◄── solo lee broker_client  │
│  │ (chmod 600)  │                              │
│  │ gitignored   │                              │
│  └──────┬───────┘                              │
│         │                                      │
│  ┌──────▼─────────┐    ┌────────────────────┐  │
│  │ BROKER CLIENT  │    │ LLM CLIENT         │  │
│  │ proceso aparte │    │ proceso aparte     │  │
│  │ tiene secretos │    │ SIN acceso a .env  │  │
│  └──────┬─────────┘    └─────────┬──────────┘  │
│         │                        │             │
│         │   ┌────────────────────▼──┐          │
│         │   │ PROMPT BUILDER        │          │
│         │   │ dict allowlist        │          │
│         │   │ (precios, posiciones, │          │
│         │   │  noticias — nada más) │          │
│         │   └───────────────────────┘          │
│         │                                      │
│  ┌──────▼──────────────────────────────────┐   │
│  │ DECISION SERVICE (determinista)         │   │
│  │ valida JSON → chequea riesgo → ejecuta  │   │
│  └─────────────────────────────────────────┘   │
└────────────────────────────────────────────────┘
```

### Reglas duras de implementación

1. **Allowlist, no denylist.** El prompt se construye con un diccionario explícito de campos permitidos. Nunca `json.dumps(config)`, nunca `os.environ`. Si un campo no está en la lista, no existe para el modelo.
2. **El LLM no tiene herramienta de ejecución.** No hay function calling hacia el broker. El modelo devuelve JSON y punto.
3. **Validación de esquema con Pydantic.** JSON que no calza con el schema → rechazado, se registra, no se ejecuta.
4. **Filtro de redacción en logs.** Regex sobre patrones de API key antes de escribir cualquier log o traza.
5. **Idempotencia obligatoria.** Cada orden lleva un `client_order_id` determinista (hash de `fecha+símbolo+decisión`). Si n8n reintenta, el broker rechaza el duplicado. **Sin esto, un reintento te compra dos veces.** ChatGPT no lo menciona y es de los bugs más caros posibles.
6. **Reconciliación cada ciclo.** Antes de decidir, compara tu estado interno con el estado autoritativo del broker. Si divergen → *halt* y alerta. Nunca operes sobre estado local asumido.
7. **Dead man's switch.** Si el proceso no manda heartbeat en 15 minutos, el flag de "órdenes habilitadas" se apaga solo. El kill switch de ChatGPT solo funciona si el sistema está vivo para escucharlo.
8. **Límite duro fuera del código.** Mantén en la cuenta del broker únicamente el capital que autorizas. Es el único límite que un bug no puede saltarse.

---

## 7. Arquitectura

Conservo la estructura de ChatGPT y agrego las cuatro piezas que faltan (en **negrita**).

```
                    ┌─────────────────┐
                    │  n8n SCHEDULER  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  ┌──────────┐        ┌──────────┐         ┌──────────┐
  │ MARKET   │        │  NEWS /  │         │ BROKER   │
  │ DATA     │        │  SEC     │         │ ADAPTER  │
  └────┬─────┘        └────┬─────┘         └────┬─────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           ▼
                 ┌───────────────────┐
                 │  RECONCILIATION   │ ◄── NUEVO: estado
                 │  divergencia→HALT │     broker vs. local
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │  SCORING ENGINE   │
                 │  (mecánico)       │
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │  LLM ANALYST      │
                 │  → JSON propuesta │
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │  RISK ENGINE      │
                 │  reglas duras     │
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │  ORDER SERVICE    │
                 │  idempotente      │ ◄── NUEVO: client_order_id
                 └─────────┬─────────┘
                           ▼
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌──────────┐     ┌──────────────┐   ┌─────────────┐
  │ POSTGRES │     │ TAX LEDGER   │   │  TELEGRAM   │
  │          │     │ FIFO / DJ1929│   │  + Kill Sw. │
  └──────────┘     └──────────────┘   └─────────────┘
                          ▲
                          └── NUEVO: obligatorio Chile
```

**Cuarta pieza nueva:** `EXECUTION QUALITY` — registra para cada orden el precio de decisión vs. precio de fill, y acumula el slippage. Sin esto no sabes si tu estrategia funciona pero la ejecución te la come.

### Modelo de datos (sobre el de ChatGPT)

Sus tablas están bien. Agrega:

```sql
tax_lots           -- FIFO, DJ 1929 (sección 2)
fx_rates           -- dólar observado por fecha, para conversión CLP
executions         -- decisión vs. fill, slippage, latencia
reconciliations    -- snapshots broker vs. local, divergencias
theses             -- tesis + invalidadores por posición (sección 5)
kill_switch_events -- quién/qué/cuándo detuvo el sistema
```

Y en `ai_decisions`, agrega `prompt_hash` y `model_version`: cuando el modelo cambie de versión, tus métricas históricas dejan de ser comparables y necesitas saber cuándo pasó.

---

## 8. Stack

Aprovechando lo que ya manejas (Docker, Postgres/Supabase, n8n, FastAPI):

| Capa | Elección | Por qué |
|---|---|---|
| Orquestación | **n8n** | Ya lo usas. Cron, notificaciones, reintentos. |
| Lógica | **Python + FastAPI** | La lógica financiera NO va en n8n. n8n llama endpoints. |
| Backtesting | **vectorbt** o **backtesting.py** | No escribas tu propio motor. |
| Datos | **yfinance** (dev) → **EODHD** o **Financial Modeling Prep** (prod) | yfinance no es para producción. |
| Fundamentales | **SEC EDGAR full-text API** | Gratis, oficial, con fechas de publicación reales. |
| Base de datos | **Postgres** (Supabase o Docker local) | Ya lo conoces. |
| Broker | **Adapter pattern** | Interfaz abstracta; Alpaca/eToro/IBKR/manual son implementaciones. |
| Secretos | **Docker secrets** o `.env` chmod 600, gitignored | Vault cuando tengas capital real. |
| Alertas | **Telegram Bot API** | Con botones inline para aprobar. |

**El adapter es la decisión de arquitectura más importante.** Define esto el día 1:

```python
class BrokerAdapter(Protocol):
    def get_positions(self) -> list[Position]: ...
    def get_cash(self) -> Money: ...
    def place_order(self, order: Order, idempotency_key: str) -> OrderResult: ...
    def get_order_status(self, order_id: str) -> OrderStatus: ...
    def is_market_open(self) -> bool: ...
```

Implementaciones: `PaperAdapter`, `AlpacaAdapter`, `EtoroAdapter`, `IBKRAdapter`, `ManualTelegramAdapter`. Cambiar de broker se vuelve una línea de configuración, y todo el bloqueador #1 deja de ser existencial.

---

## 9. Plan de fases con criterios de salida cuantitativos

ChatGPT propone 4 fases pero sin criterios objetivos de avance. Sin eso, siempre encontrarás una razón para pasar a la siguiente.

### Fase 0 — Simulador (semanas 1–4)
- Adapter + PaperAdapter + Postgres + motor de scoring mecánico + Risk Engine + backtest walk-forward
- **Criterio de salida:** el componente mecánico bate a buy & hold de SPY, después de costos, en **al menos 3 de 4 ventanas walk-forward independientes**. Si no → ajusta la estrategia, no los criterios.

### Fase 1 — Paper trading (semanas 5–17, mínimo 60 días)
- Todo corriendo en vivo contra paper. LLM incluido. Notificación diaria a Telegram.
- **Criterio de salida (todos):**
  - ≥ 40 decisiones registradas
  - Max drawdown < 15%
  - Sharpe > 0,5 (no > 2 — desconfía de eso en 60 días)
  - **Cero** discrepancias de reconciliación no explicadas
  - **Cero** órdenes duplicadas
  - Kill switch probado ≥ 3 veces con éxito
- Nota: 60 días no prueban nada estadísticamente sobre retorno. Prueban que **el sistema no está roto**. Ese es el objetivo real.

### Fase 2 — Real con capital de matrícula (semanas 18–30)
- USD 200–500. Objetivo: medir slippage, latencia, y tu propia reacción emocional.
- **Criterio de salida:** slippage promedio < 0,3% por operación; tasa de fallos de ejecución < 1%; tú tranquilo con el proceso.

### Fase 3 — Capital significativo (semana 30+)
- Solo si las tres fases anteriores pasaron **con sus criterios originales, sin renegociarlos**.
- Autonomía plena **jamás**. Aprobación humana para: nuevas posiciones, cambios de parámetros de riesgo, y cualquier operación > 5% del portafolio. Automatizado: ventas defensivas y rebalanceo dentro de límites.

---

## 10. MVP: primeras 8 semanas, semana a semana

| Sem | Entregable | Definición de listo |
|---|---|---|
| 1 | Docker + Postgres + esquema + `BrokerAdapter` + `PaperAdapter` | Test: comprar/vender simulado, posiciones persisten |
| 2 | Ingesta de datos de mercado + universo point-in-time | 3 años de OHLCV diario para 50 tickers |
| 3 | Motor de scoring mecánico (momentum, valoración, calidad) | Score reproducible para cualquier fecha histórica |
| 4 | Motor de backtest + walk-forward | Reporte contra SPY, con costos modelados |
| 5 | Risk Engine + Order Service idempotente | Test: doble llamada = una sola orden |
| 6 | LLM Analyst con schema Pydantic + prompt allowlist | Test: secreto inyectado en config NO aparece en el prompt |
| 7 | Telegram: reporte diario, propuesta, kill switch, aprobación | Ciclo completo end-to-end en paper |
| 8 | Tax Ledger FIFO + reconciliación + panel | DJ 1929 borrador generado desde datos simulados |

Semana 9 en adelante: correr y observar. Sin tocar la estrategia por 60 días. **Esa disciplina es la parte más difícil del proyecto.**

---

## 11. Qué verificar esta semana (bloqueantes)

- [ ] **Alpaca**: email a `support@alpaca.markets` — "Can a Chilean tax resident open a live trading account?"
- [ ] **eToro**: crear cuenta, ir a Settings → Trading → API Key Management, confirmar que se pueden generar claves desde Chile. **Y confirmar si te dan acciones reales o CFDs.**
- [ ] **IBKR**: iniciar solicitud de cuenta cash (sin mínimo). El onboarding toma días; empiézalo ahora aunque no lo uses.
- [ ] **Racional**: preguntar por chat de soporte si hay API en roadmap y si permiten acceso programático. Guarda la respuesta por escrito.
- [ ] **Contador**: consulta sobre compensación de pérdidas de fuente extranjera y sobre el tratamiento de CFDs si eliges eToro.

**Mientras tanto, empieza la Ruta D.** No depende de ninguna de estas respuestas.

---

## 12. Lo que honestamente deberías saber antes de empezar

- La mayoría de los sistemas de trading algorítmico retail pierden frente a comprar y mantener un índice, principalmente por costos, impuestos y sobreajuste. Eso no significa que el tuyo vaya a perder, pero sí que la hipótesis nula es "esto no funciona" y la carga de la prueba está en el sistema.
- El valor más probable de este proyecto no es financiero. Es que vas a construir un pipeline de datos con reconciliación, idempotencia, auditoría de decisiones de IA y control de riesgo determinista sobre salidas de modelo. Ese es exactamente el tipo de arquitectura que estás diseñando en tu trabajo. Como laboratorio, vale mucho más que los USD 300.
- **Señales de que hay que parar:** drawdown mensual > 10%; te sorprendes ajustando criterios de salida para poder avanzar de fase; revisas el portafolio más de 3 veces al día; o empiezas a agregar capital para "recuperar".

---

## 13. Decisión que necesito de ti

**¿Qué ruta de broker tomamos como primaria para la Fase 1?**

- **A** — Alpaca paper (mejor herramienta, live incierto en Chile)
- **B** — eToro API (funciona desde Chile con alta probabilidad, verificar CFD vs. acción real)
- **C** — IBKR (más robusto, más fricción)
- **D** — Racional + ejecución manual (arrancable hoy, cero riesgo)

Mi lectura: **A para construir + D en paralelo desde ya**, y decidir entre B y C recién en la semana 8, cuando tengas el adapter listo y las respuestas de soporte en la mano. Así ninguna de las cuatro verificaciones te bloquea.
