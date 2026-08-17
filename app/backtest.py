"""Backtest walk-forward del componente mecánico, con costos explícitos.

Reglas de honestidad (las que matan backtests cuando faltan):
- Sin look-ahead: la decisión del día i usa datos hasta el día i-1.
- Costos modelados: comisión + spread + slippage por lado en cada rebalanceo.
- Sin optimización: parámetros fijos declarados en app/scoring.py; las 4
  ventanas son evaluación secuencial pura, no búsqueda de parámetros.
- Limitación conocida (documentada): el universo actual parte hoy, no hay
  constituyentes históricos → el resultado tiene survivorship bias y por eso
  el veredicto de esta fase es provisorio hasta cargar universo point-in-time.

Nota de diseño: el plan sugería vectorbt/backtesting.py. Para una cartera
cross-sectional con rebalanceo mensual, un simulador vectorizado explícito de
~100 líneas es más auditable que una dependencia grande; si la estrategia se
complejiza (órdenes intradía, stops en el backtest), se migra.
"""

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import PriceBar
from app.scoring import LOOKBACK, SKIP, momentum_scores
from app.universe import BENCHMARK


@dataclass
class BacktestConfig:
    top_n: int = 5
    cost_per_side: float = 0.002  # 0,2% por lado: comisión + spread + slippage
    n_windows: int = 4
    benchmark: str = BENCHMARK


@dataclass
class WindowResult:
    start: date
    end: date
    strategy_return: float
    benchmark_return: float

    @property
    def beats(self) -> bool:
        return self.strategy_return > self.benchmark_return


@dataclass
class BacktestResult:
    equity: pd.Series
    bench_equity: pd.Series
    windows: list[WindowResult] = field(default_factory=list)
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    total_costs_pct: float = 0.0
    config: BacktestConfig = field(default_factory=BacktestConfig)

    @property
    def wins(self) -> int:
        return sum(1 for w in self.windows if w.beats)

    @property
    def passed(self) -> bool:
        """Criterio de salida fase 2: bate al benchmark en ≥3 de 4 ventanas."""
        return self.wins >= 3

    @property
    def strategy_total(self) -> float:
        # Ambas series parten de base 1,0 ANTES del primer día simulado, así el
        # costo del rebalanceo inicial cuenta (dividir por iloc[0] lo cancelaría).
        return float(self.equity.iloc[-1] - 1.0)

    @property
    def benchmark_total(self) -> float:
        return float(self.bench_equity.iloc[-1] - 1.0)


def load_close_matrix(session_factory: sessionmaker[Session]) -> pd.DataFrame:
    """Matriz fechas × símbolos con precios de cierre desde la base de datos."""
    with session_factory() as s:
        rows = s.execute(select(PriceBar.date, PriceBar.symbol, PriceBar.close)).all()
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows, columns=["date", "symbol", "close"])
    frame["close"] = frame["close"].astype(float)
    return frame.pivot_table(index="date", columns="symbol", values="close").sort_index()


def run_backtest(closes: pd.DataFrame, config: BacktestConfig | None = None) -> BacktestResult:
    config = config or BacktestConfig()
    closes = closes.sort_index()
    if config.benchmark not in closes.columns:
        raise ValueError(f"Falta el benchmark {config.benchmark} en los datos")

    candidates = [c for c in closes.columns if c != config.benchmark]
    returns = closes.pct_change().fillna(0.0)
    months = pd.Series(
        [d.month for d in closes.index], index=closes.index
    )

    start_i = LOOKBACK + SKIP + 1
    if len(closes) <= start_i + 40:
        raise ValueError(
            f"Historia insuficiente: hay {len(closes)} días y se necesitan >{start_i + 40}"
        )

    weights = pd.Series(0.0, index=candidates)
    equity_values: list[float] = []
    daily_strategy_returns: list[float] = []
    total_costs = 0.0
    equity = 1.0

    for i in range(start_i, len(closes)):
        cost_today = 0.0
        first_day_of_month = months.iloc[i] != months.iloc[i - 1]
        if first_day_of_month or i == start_i:
            # Decide con datos hasta AYER (i-1); opera con el retorno de HOY.
            scores = momentum_scores(closes[candidates], at=i - 1)
            if not scores.empty:
                top = scores.nlargest(config.top_n).index
                new_weights = pd.Series(0.0, index=candidates)
                new_weights[top] = 1.0 / len(top)
                turnover = float((new_weights - weights).abs().sum())
                cost_today = turnover * config.cost_per_side
                total_costs += cost_today
                weights = new_weights

        day_return = float((weights * returns.iloc[i][candidates]).sum()) - cost_today
        equity *= 1.0 + day_return
        equity_values.append(equity)
        daily_strategy_returns.append(day_return)

    span = closes.index[start_i:]
    equity_series = pd.Series(equity_values, index=span)
    bench_returns = returns[config.benchmark].iloc[start_i:]
    bench_series = (1.0 + bench_returns).cumprod()  # base 1,0, igual que la estrategia

    windows = _split_windows(equity_series, bench_series, config.n_windows)

    strat = pd.Series(daily_strategy_returns)
    sharpe = float(strat.mean() / strat.std() * (252**0.5)) if strat.std() > 0 else 0.0
    running_max = equity_series.cummax()
    max_dd = float((equity_series / running_max - 1.0).min())

    return BacktestResult(
        equity=equity_series,
        bench_equity=bench_series,
        windows=windows,
        sharpe=sharpe,
        max_drawdown=max_dd,
        total_costs_pct=total_costs,
        config=config,
    )


def _split_windows(
    equity: pd.Series, bench: pd.Series, n_windows: int
) -> list[WindowResult]:
    size = len(equity) // n_windows
    windows: list[WindowResult] = []
    for k in range(n_windows):
        lo = k * size
        hi = (k + 1) * size - 1 if k < n_windows - 1 else len(equity) - 1
        windows.append(
            WindowResult(
                start=equity.index[lo],
                end=equity.index[hi],
                strategy_return=float(equity.iloc[hi] / equity.iloc[lo] - 1),
                benchmark_return=float(bench.iloc[hi] / bench.iloc[lo] - 1),
            )
        )
    return windows
