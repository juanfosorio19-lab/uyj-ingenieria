# Simulación de impuestos en Chile

> No es asesoría tributaria. Valores UTA/UTM y tipo de cambio son aproximados (agosto 2026); las cifras exactas las fija el SII cada año. Supuestos: UTA ≈ CLP 820.000, dólar ≈ CLP 950.

## 1. Las reglas en 4 líneas

1. Cada **venta con ganancia** de una acción extranjera tributa en el **Impuesto Global Complementario (IGC)**: la ganancia se suma a tu sueldo y demás rentas del año, y paga tu tasa marginal (0–40%).
2. El costo se calcula **FIFO** y todo se convierte a CLP **al tipo de cambio de la fecha de cada operación** (compra y venta por separado).
3. Mientras **no vendas**, no pagas: el impuesto se difiere indefinidamente (por eso el diseño de baja rotación).
4. **DJ 1929** cada año (vence 30 de junio) aunque hayas perdido o no hayas vendido nada, y **F22** en abril. Vía CRS el SII recibe datos de brokers extranjeros asociados a tu RUT: no declarar es detectable.

## 2. Tabla IGC (tramos anuales, aproximados en pesos)

| Renta anual tributable | Tasa marginal |
|---|---|
| hasta ~$11,1M (13,5 UTA) | **exento** |
| ~$11,1M – $24,6M | 4% |
| ~$24,6M – $41,0M | 8% |
| ~$41,0M – $57,4M | 13,5% |
| ~$57,4M – $73,8M | 23% |
| ~$73,8M – $98,4M | 30,4% |
| ~$98,4M – $254M | 35% |
| sobre ~$254M | 40% |

Tu sueldo ya "llena" los tramos de abajo (el impuesto que retiene tu empleador se usa como crédito), así que **las ganancias del agente pagan la tasa del tramo donde cae tu sueldo, o el siguiente si lo empujan hacia arriba**.

## 3. Micro-ejemplo: una sola operación (y el efecto dólar)

Compras 10 NVDA a USD 100 con dólar a $900. Vendes a USD 120 con dólar a $950.

```
Costo   = 10 × 100 × 900 = CLP   900.000
Venta   = 10 × 120 × 950 = CLP 1.140.000
Ganancia tributable      = CLP   240.000
```

Ojo con el detalle: de esos $240.000, solo ~$190.000 vienen de la acción; **~$50.000 vienen de la subida del dólar**. Si la acción quedara plana pero el dólar sube de 900 a 950, igual tienes ganancia tributable de $50.000 al vender. El agente registra ambos FX en `tax_lots` precisamente por esto.

## 4. Simulación anual: sueldo × ganancia del agente

Impuesto adicional que pagas en abril por las ganancias **realizadas** del agente (asumiendo que no te cambian de tramo):

| Sueldo tributable mensual | Tramo | Ganancia USD 500 (~$475k) | USD 2.000 (~$1,9M) | USD 5.000 (~$4,75M) |
|---|---|---|---|---|
| $900.000 | exento | $0 | ~$76.000* | ~$296.000* |
| $1.500.000 | 4% | **$19.000** | $76.000 | ~$220.000* |
| $2.500.000 | 8% | **$38.000** | $152.000 | ~$400.000* |
| $4.000.000 | 13,5% | **$64.000** | $256.500 | ~$641.000 |
| $5.500.000 | 23% | **$109.000** | $437.000 | ~$1.092.500 |

\* casos donde la ganancia cruza al tramo siguiente; cifra aproximada mezclando tasas.

Lectura práctica: con el capital de las fases 5–6 (USD 500–10.000) y retornos realistas, **el impuesto anual del agente se mueve entre $0 y ~$500.000**. No es lo que mata el proyecto — lo que mata es la rotación alta combinada con tramos altos.

## 5. El costo de rotar: mismo retorno, distinto bolsillo

Capital USD 10.000, retorno 8% anual, tramo marginal 23%, horizonte 10 años:

| Estrategia | Resultado a 10 años (después de IGC) |
|---|---|
| Rotación alta (realiza y paga cada año) | ~USD 18.180 |
| Baja rotación (realiza al final, difiere 10 años) | ~USD 18.920 |

Diferir el impuesto vale ~USD 740 (7,4% del capital) sin cambiar la estrategia en nada. En tramo 35% la brecha casi se duplica. **Es la justificación numérica de la cadencia semanal/mensual y del horizonte ≥5 días del plan.**

## 6. Dividendos de acciones USA

Con el tratado Chile–EE.UU. (vigente desde dic-2023) y el formulario **W-8BEN** presentado al broker, EE.UU. retiene **15%** (en vez de 30%). En Chile ese dividendo también va al IGC, con crédito por lo retenido afuera (art. 41 A). Para un portafolio chico el efecto es menor, pero el W-8BEN hay que firmarlo al abrir la cuenta — un click que ahorra la mitad de la retención.

## 7. Calendario anual (lo automatizable y lo firmable)

| Fecha | Qué | Quién |
|---|---|---|
| Enero | Borrador DJ 1929 generado desde `tax_lots` | **El agente, solo** |
| Abril | F22 (renta) — incluye las ganancias del año anterior | Tú firmas (con el borrador listo) |
| 30 junio | DJ 1929 presentada | Tú/contador (con el borrador listo) |

## 8. Preguntas concretas para el contador (consulta única, ~$50–150)

1. ¿Aplica a acciones **extranjeras** la exención del art. 57 LIR para trabajadores dependientes (ganancias de capital ≤ 30 UTM ≈ $2,1M)? Si aplica, con capital chico podrías pagar **cero** — el criterio del SII es restrictivo y hay que confirmarlo.
2. ¿Puedo **netear pérdidas** de fuente extranjera contra ganancias del mismo año (arts. 41 A/41 B)?
3. Si terminara usando un broker que ofrece CFDs en vez de acciones reales: ¿tratamiento tributario? (motivo suficiente para preferir acciones reales).
