from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.backtest import BacktestConfig, run_backtest
from app.data.edgar import extract_annual_revenue, revenue_growth_yoy
from app.db import make_session_factory
from app.eligibility import build_eligibility, membership_mask
from app.models import Fundamental, UniverseMember
from app.universe import load_universe_csv
from tests.test_backtest import synthetic_closes

FACTS = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "val": 100, "filed": "2024-02-15", "form": "10-K"},
                        {"end": "2024-12-31", "val": 120, "filed": "2025-02-14", "form": "10-K"},
                        {"end": "2024-12-31", "val": 121, "filed": "2025-06-01", "form": "10-K"},
                        {"end": "2024-06-30", "val": 30, "filed": "2024-07-30", "form": "10-Q"},
                    ]
                }
            }
        }
    }
}


def test_extract_annual_revenue_prefers_first_filing_and_ignores_quarters():
    rows = extract_annual_revenue(FACTS)
    assert len(rows) == 2  # los 10-Q no cuentan; el refile de 2024 no duplica
    assert rows[0]["period_end"] == date(2023, 12, 31)
    assert rows[1]["filed"] == date(2025, 2, 14)  # primer filed gana


def seed_fundamentals(engine, symbol="WIN", growths=((2023, 100), (2024, 80))):
    with Session(engine) as s:
        for year, value in growths:
            s.add(
                Fundamental(
                    symbol=symbol, metric="revenue_annual",
                    period_end=date(year, 12, 31), value=Decimal(value),
                    filed=date(year + 1, 2, 15), form="10-K",
                )
            )
        s.commit()


def test_revenue_growth_is_point_in_time(engine):
    seed_fundamentals(engine)  # 2024 cae 20% vs 2023, publicado el 2025-02-15
    sf = make_session_factory(engine)
    # antes de la publicación del 10-K 2024, solo existe UN dato => None
    assert revenue_growth_yoy(sf, "WIN", as_of=date(2025, 1, 1)) is None
    # después de publicado: crecimiento negativo conocido
    growth = revenue_growth_yoy(sf, "WIN", as_of=date(2025, 3, 1))
    assert growth is not None and growth < 0


def test_membership_mask_only_with_real_history(engine):
    sf = make_session_factory(engine)
    closes = synthetic_closes(days=300)
    with Session(engine) as s:  # lista sembrada: sin valid_to => sin máscara
        s.add(UniverseMember(symbol="WIN", valid_from=date(2026, 1, 1), valid_to=None))
        s.commit()
    assert membership_mask(sf, closes.index, list(closes.columns)) is None

    with Session(engine) as s:  # historia real: WIN sale del índice a mitad de período
        s.add(UniverseMember(symbol="FLAT", valid_from=date(2000, 1, 1),
                             valid_to=date(2024, 6, 28)))
        s.commit()
    mask = membership_mask(sf, closes.index, list(closes.columns))
    assert mask is not None
    assert bool(mask["FLAT"].iloc[0]) is True
    assert bool(mask["FLAT"].iloc[-1]) is False  # ya no es miembro al final


def test_eligibility_changes_backtest_selection(engine):
    sf = make_session_factory(engine)
    closes = synthetic_closes(days=420)
    baseline = run_backtest(closes, BacktestConfig(top_n=1))

    # fundamentales dicen: los ingresos de WIN caen (publicado antes del período)
    seed_fundamentals(engine, symbol="WIN", growths=((2022, 100), (2023, 80)))
    eligible = build_eligibility(sf, closes)
    assert eligible is not None
    filtered = run_backtest(closes, BacktestConfig(top_n=1), eligible=eligible)

    # sin WIN disponible, la estrategia rinde menos que con él
    assert filtered.strategy_total < baseline.strategy_total


def test_universe_csv_loader(engine, tmp_path):
    csv_path = tmp_path / "universo.csv"
    csv_path.write_text(
        "symbol,valid_from,valid_to\nAAPL,2015-01-01,\nGE,2015-01-01,2018-06-26\n",
        encoding="utf-8",
    )
    sf = make_session_factory(engine)
    msg = load_universe_csv(sf, str(csv_path))
    assert "2 vigencias" in msg
    with Session(engine) as s:
        rows = s.query(UniverseMember).all()
        assert {r.symbol for r in rows} == {"AAPL", "GE"}
        ge = next(r for r in rows if r.symbol == "GE")
        assert ge.valid_to == date(2018, 6, 26)
