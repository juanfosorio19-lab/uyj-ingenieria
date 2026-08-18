"""Experimentos de estrategia — hipótesis declaradas, veredicto con datos.

Experimento "chase" (hipótesis de Juan, 18-08-2026): comprar cada día el
mayor ganador de ayer del universo, mantener un día, rotar. ¿Captura los
"flancos de subida" o los persigue tarde y paga los costos?

Se evalúa con los MISMOS datos y costos que la estrategia oficial. El
resultado depende de si los retornos diarios persisten (momentum de 1 día)
o revierten — es una pregunta empírica, no de opinión.
"""

from dataclasses import dataclass

import pandas as pd

from app.universe import BENCHMARK


@dataclass
class ChaseResult:
    chase_total: float  # retorno total de perseguir al ganador de ayer
    benchmark_total: float
    trades: int
    cost_drag: float  # cuánto retorno se fue SOLO en costos

    def summary(self) -> str:
        verdict = (
            "✅ persiguió y ganó" if self.chase_total > self.benchmark_total
            else "❌ perseguir PERDIÓ contra comprar y mantener SPY"
        )
        return (
            "🧪 Experimento: comprar cada día el mayor ganador de AYER\n"
            f"Resultado: {self.chase_total:+.1%} · SPY: {self.benchmark_total:+.1%} → {verdict}\n"
            f"Operaciones: {self.trades} · Retorno comido solo por costos: "
            f"{self.cost_drag:+.1%}\n"
            "(mismos datos y costos que la estrategia oficial; "
            "con dinero real además pagaría impuestos por CADA ganancia y "
            "chocaría con la regla PDT bajo USD 25.000)"
        )


def chase_backtest(
    closes: pd.DataFrame,
    cost_per_side: float = 0.002,
    benchmark: str = BENCHMARK,
) -> ChaseResult:
    if benchmark not in closes.columns:
        raise ValueError(f"Falta el benchmark {benchmark}")
    candidates = [c for c in closes.columns if c != benchmark]
    if not candidates or len(closes) < 30:
        raise ValueError("Historia insuficiente para el experimento")

    returns = closes[candidates].pct_change()
    equity = 1.0
    cost_only = 1.0  # cuánto queda de 1.0 pagando SOLO los costos del giro diario
    previous_pick: str | None = None
    trades = 0

    for i in range(2, len(closes)):
        yesterday = returns.iloc[i - 1].dropna()
        if yesterday.empty:
            continue
        pick = yesterday.idxmax()  # el "flanco de subida" de ayer
        cost = 0.0
        if pick != previous_pick:
            # vender lo de ayer + comprar lo de hoy (la primera vez, solo comprar)
            cost = cost_per_side * (2 if previous_pick is not None else 1)
            trades += 1
            previous_pick = pick
        day_return = returns.iloc[i].get(pick)
        day_return = 0.0 if pd.isna(day_return) else float(day_return)
        equity *= 1.0 + day_return - cost
        cost_only *= 1.0 - cost

    bench = closes[benchmark].iloc[2:]
    benchmark_total = float(bench.iloc[-1] / bench.iloc[0] - 1)
    return ChaseResult(
        chase_total=equity - 1.0,
        benchmark_total=benchmark_total,
        trades=trades,
        cost_drag=cost_only - 1.0,
    )
