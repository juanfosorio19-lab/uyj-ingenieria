from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.backtest import BacktestConfig, load_close_matrix, run_backtest
from app.db import make_session_factory
from app.models import PriceBar
from app.report_backtest import build_backtest_html, summary_text, write_report
from app.scoring import momentum_scores


def synthetic_closes(days: int = 420) -> pd.DataFrame:
    """WIN sube fuerte, SPY sube poco, FLAT no se mueve, DOWN cae.

    Determinista: sin azar, el test siempre da lo mismo.
    """
    idx = pd.bdate_range("2024-01-02", periods=days)
    frame = pd.DataFrame(
        {
            "WIN": [100 * (1.002**i) for i in range(days)],
            "SPY": [100 * (1.0003**i) for i in range(days)],
            "FLAT": [100.0] * days,
            "DOWN": [100 * (0.999**i) for i in range(days)],
        },
        index=idx,
    )
    return frame


def test_momentum_picks_the_winner():
    closes = synthetic_closes()
    scores = momentum_scores(closes[["WIN", "FLAT", "DOWN"]], at=len(closes) - 1)
    assert scores.idxmax() == "WIN"
    assert scores["DOWN"] < 0


def test_momentum_requires_enough_history():
    closes = synthetic_closes(days=50)
    assert momentum_scores(closes, at=49).empty


def test_backtest_beats_weak_benchmark_and_reports_windows():
    closes = synthetic_closes()
    result = run_backtest(closes, BacktestConfig(top_n=1))

    assert len(result.windows) == 4
    assert result.passed  # WIN crece 0,2%/día vs SPY 0,03%/día
    assert result.strategy_total > result.benchmark_total
    assert result.max_drawdown <= 0
    assert result.total_costs_pct > 0  # los costos existen y se cobraron


def test_costs_reduce_returns():
    closes = synthetic_closes()
    cheap = run_backtest(closes, BacktestConfig(top_n=2, cost_per_side=0.0))
    expensive = run_backtest(closes, BacktestConfig(top_n=2, cost_per_side=0.01))
    assert expensive.strategy_total < cheap.strategy_total


def test_backtest_needs_benchmark_and_history():
    closes = synthetic_closes()
    with pytest.raises(ValueError, match="benchmark"):
        run_backtest(closes[["WIN", "FLAT"]])
    with pytest.raises(ValueError, match="insuficiente"):
        run_backtest(synthetic_closes(days=160))


def test_html_report_and_summary(tmp_path):
    result = run_backtest(synthetic_closes(), BacktestConfig(top_n=1))
    html = build_backtest_html(result)
    assert "<svg" in html
    assert "SPY" in html
    assert "survivorship" in html  # la advertencia de honestidad está presente
    path = write_report(result, tmp_path / "backtest.html")
    assert path.exists()
    assert "Backtest walk-forward" in summary_text(result) or "🧪" in summary_text(result)


def test_load_close_matrix_from_db(engine):
    sf = make_session_factory(engine)
    with Session(engine) as s:
        for day, price in [(date(2026, 8, 13), "100"), (date(2026, 8, 14), "110")]:
            s.add(
                PriceBar(
                    symbol="AAPL",
                    date=day,
                    open=Decimal(price),
                    high=Decimal(price),
                    low=Decimal(price),
                    close=Decimal(price),
                    volume=100,
                )
            )
        s.commit()
    matrix = load_close_matrix(sf)
    assert matrix.shape == (2, 1)
    assert float(matrix["AAPL"].iloc[-1]) == 110.0
