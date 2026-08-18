"""Scoring mecánico — factores calculables solo con precios.

Hipótesis declarada ANTES de mirar resultados (anti p-hacking):
    "Cartera equiponderada de los top-N por momentum 6m (excluyendo el último
    mes), rebalanceada mensualmente, bate a SPY después de costos."

Parámetros fijos, sin optimización: 1 solo grado de libertad ya declarado.
Los factores fundamentales (valoración/calidad) entran cuando tengamos
SEC EDGAR con fechas de publicación reales — usarlos sin eso es look-ahead.
"""

import pandas as pd

LOOKBACK = 126  # ~6 meses de ruedas
SKIP = 21  # excluye el último mes (reversión de corto plazo)


def momentum_scores(closes: pd.DataFrame, at: int) -> pd.Series:
    """Score de momentum usando SOLO datos hasta la fila `at` (inclusive).

    score = precio[at - SKIP] / precio[at - SKIP - LOOKBACK] - 1
    Devuelve una Series por símbolo, sin los que no tienen historia suficiente.
    """
    if at - SKIP - LOOKBACK < 0:
        return pd.Series(dtype=float)
    recent = closes.iloc[at - SKIP]
    past = closes.iloc[at - SKIP - LOOKBACK]
    scores = recent / past - 1
    return scores.dropna()
