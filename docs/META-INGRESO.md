# Meta: ingreso mensual desde el agente

> Registrado el 18-08-2026. Meta declarada por Juan: retirar ~CLP 300.000/mes
> como ingreso extra al sueldo, y a largo plazo vivir de esto.

## La ecuación que gobierna todo

Un retiro mensual sostenible (sin comerse el capital) no puede superar el
retorno neto del portafolio. Con un retorno **bueno y sostenible** de 8% anual
neto (después de costos, spread FX e impuestos — ya sería ganarle al mercado):

```
capital necesario = retiro anual / retorno neto
CLP 300.000 × 12 / 0,08 = CLP 45.000.000 (≈ USD 49.000)
```

| Capital invertido | Retiro mensual sostenible @8% neto |
|---|---|
| CLP 10.000 | CLP 66 (sí: sesenta y seis pesos) |
| CLP 1.000.000 | CLP 6.600 |
| CLP 10.000.000 | CLP 66.000 |
| **CLP 45.000.000** | **CLP 300.000** ← la meta |
| CLP 300.000.000 | CLP 2.000.000 (un sueldo: "vivir del trading") |

**Retirar 300.000/mes con menos capital que eso es consumir el capital**, no
generar ingreso: con CLP 5M y retiros de 300k/mes, la cuenta muere en ~17
meses aunque la estrategia gane.

## Sobre "la gente que vive del trading"

Los que de verdad viven de esto caen en dos grupos: los que tienen capital
grande (la tabla de arriba: un sueldo exige cientos de millones de CLP), y los
que venden cursos sobre cómo vivir del trading. Los estudios académicos sobre
day traders retail (Barber & Odean, mercado taiwanés completo, 15 años de
datos) encuentran que **menos del 1% es consistentemente rentable**. El plan
de este proyecto lo asume desde el día uno: la hipótesis nula es "esto no
funciona" y la carga de la prueba está en el backtest y los 60 días de paper.

## La trayectoria que SÍ funciona con estos números

La misma cifra (300.000/mes) invertida en dirección contraria — **aporte** en
vez de retiro — construye el capital que después paga el retiro:

| Años aportando CLP 300.000/mes @8% neto | Capital acumulado |
|---|---|
| 3 | ~CLP 12M |
| 5 | ~CLP 22M |
| 7 | ~CLP 33M |
| **~9,5** | **~CLP 45M → desde aquí el retiro de 300k/mes se paga solo, para siempre** |

Retirar las ganancias durante la fase de acumulación mata el interés
compuesto — es exactamente la fuerza que hace alcanzable la meta.

## Qué cambia en el agente (y qué no)

**No cambia nada del motor**: señales, riesgo, salidas, impuestos y fases
siguen igual. Un retiro es simplemente vender un % y transferir — cualquier
portafolio lo soporta; no requiere "estrategia de ingreso".

**Se agrega en la fase 6** (cuando haya capital real y validado):

1. **Regla de retiro sobre high-water mark**: solo se puede retirar si el
   equity supera su máximo histórico; el retiro máximo del mes es una fracción
   del excedente. Protege el capital por construcción: en rachas malas no hay
   retiro, jamás se come el principal.
2. **Panel de meta en el reporte mensual**: capital actual vs. los 45M,
   proyección de fecha de "ingreso sostenible", y cuánto sería retirable hoy.
3. **Retiros trimestrales, no mensuales, mientras el monto sea chico**: cada
   conversión USD→CLP paga 0,5–1% de spread; 12 conversiones al año de montos
   chicos es regalar una parte del retorno.

## Regla de decisión simple

- Capital < 45M → **todo aporte, cero retiro** (fase de construcción).
- Capital ≥ 45M y agente validado → activar la regla de retiro high-water mark.
- Las cifras se recalculan con el retorno real medido del agente (no el
  supuesto 8%) cuando existan ≥12 meses de datos reales.
