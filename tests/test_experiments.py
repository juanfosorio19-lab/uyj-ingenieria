"""El experimento 'chase' debe ser JUSTO: gana cuando los retornos persisten,
pierde cuando revierten. Ambos casos con datos sintéticos deterministas."""

import pandas as pd

from app.experiments import chase_backtest


def _frame(columns: dict) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=len(next(iter(columns.values()))))
    return pd.DataFrame(columns, index=idx)


def test_chase_wins_when_winners_persist():
    """Un ganador permanente: perseguirlo equivale a mantenerlo (menos 1 costo)."""
    days = 250
    frame = _frame(
        {
            "WIN": [100 * (1.003**i) for i in range(days)],
            "FLAT": [100.0] * days,
            "SPY": [100 * (1.0002**i) for i in range(days)],
        }
    )
    result = chase_backtest(frame)
    assert result.trades == 1  # compra WIN el día 1 y nunca lo suelta
    assert result.chase_total > result.benchmark_total


def test_chase_dies_when_returns_mean_revert():
    """Si el ganador de ayer revierte hoy (lo típico intradía), perseguir sangra:
    compra siempre al que acaba de subir justo antes de que le toque bajar."""
    days = 250
    a, b = [100.0], [100.0]
    for i in range(1, days):
        if i % 2 == 1:
            a.append(a[-1] * 1.03)
            b.append(b[-1] * 0.97)
        else:
            a.append(a[-1] * 0.97)
            b.append(b[-1] * 1.03)
    frame = _frame({"A": a, "B": b, "SPY": [100 * (1.0002**i) for i in range(days)]})
    result = chase_backtest(frame)
    assert result.chase_total < -0.9  # capital casi destruido
    assert result.chase_total < result.benchmark_total
    assert result.trades > 200  # giró casi todos los días...
    assert result.cost_drag < -0.5  # ...y solo los costos ya se comen más de la mitad
    assert "PERDIÓ" in result.summary()
