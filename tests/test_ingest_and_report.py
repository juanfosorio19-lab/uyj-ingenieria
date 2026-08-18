from datetime import date, timedelta
from decimal import Decimal
from typing import ClassVar

from sqlalchemy.orm import Session

from app.data.fx import parse_mindicador
from app.data.ingest import Bar, ingest_symbol, ingest_universe
from app.db import make_session_factory
from app.models import FxRate, PriceBar
from app.report import build_daily_report
from app.universe import ensure_universe


class FakeSource:
    """Fuente determinista: dos días de datos por símbolo, precios distintos."""

    PRICES: ClassVar[dict] = {
        "AAPL": (Decimal(100), Decimal(110)),  # +10%
        "NVDA": (Decimal(100), Decimal(95)),  # -5%
        "SPY": (Decimal(100), Decimal(101)),  # +1%
    }
    D1 = date(2026, 8, 13)
    D2 = date(2026, 8, 14)

    def fetch(self, symbol, start, end):
        first, second = self.PRICES.get(symbol, (Decimal(50), Decimal(50)))
        bars = [
            Bar(self.D1, first, first, first, first, 1000),
            Bar(self.D2, second, second, second, second, 1000),
        ]
        return [b for b in bars if start <= b.date <= end]


class BrokenSource:
    def fetch(self, symbol, start, end):
        raise ConnectionError("sin red")


def test_ingest_is_incremental_and_idempotent(engine):
    sf = make_session_factory(engine)
    source = FakeSource()
    today = FakeSource.D2

    assert ingest_symbol(sf, source, "AAPL", today=today) == 2
    assert ingest_symbol(sf, source, "AAPL", today=today) == 0  # nada nuevo, nada duplicado

    with Session(engine) as s:
        rows = s.query(PriceBar).filter_by(symbol="AAPL").all()
        assert len(rows) == 2


def test_ingest_universe_tolerates_failures(engine):
    sf = make_session_factory(engine)
    summary = ingest_universe(sf, BrokenSource(), ["AAPL", "NVDA"], today=FakeSource.D2)
    assert summary.symbols_failed == ["AAPL", "NVDA"]
    assert summary.bars_added == 0
    assert "FALLARON" in summary.one_liner()


def test_universe_seeds_once(engine):
    sf = make_session_factory(engine)
    first = ensure_universe(sf)
    second = ensure_universe(sf)
    assert first == second
    assert "SPY" in first
    assert len(first) == 51  # 50 símbolos + benchmark


def test_daily_report_contains_movers_benchmark_and_health(engine):
    sf = make_session_factory(engine)
    source = FakeSource()
    for symbol in ("AAPL", "NVDA", "SPY"):
        ingest_symbol(sf, source, symbol, today=FakeSource.D2)
    with Session(engine) as s:
        s.add(FxRate(date=FakeSource.D2, clp_per_usd=Decimal("950.30")))
        s.commit()

    report = build_daily_report(sf)

    assert "AAPL +10.0%" in report
    assert "NVDA -5.0%" in report
    assert "SPY: +1.0%" in report  # benchmark aparte, no entre los movers
    assert "950.30" in report
    assert "3/3 símbolos al día" in report
    assert "Caja USD 10,000.00" in report


def test_daily_report_flags_stale_symbols(engine):
    sf = make_session_factory(engine)
    source = FakeSource()
    ingest_symbol(sf, source, "AAPL", today=FakeSource.D2)
    ingest_symbol(sf, source, "NVDA", today=FakeSource.D1)  # se queda un día atrás

    report = build_daily_report(sf)
    assert "1/2 símbolos al día" in report
    assert "NVDA" in report.split("🩺")[1]


def test_parse_mindicador():
    payload = {
        "serie": [
            {"fecha": "2026-08-14T04:00:00.000Z", "valor": 950.3},
            {"fecha": "2026-08-13T04:00:00.000Z", "valor": 948.1},
        ]
    }
    parsed = parse_mindicador(payload)
    assert parsed == (date(2026, 8, 14), Decimal("950.3"))
    assert parse_mindicador({"serie": []}) is None


def test_scheduler_next_run_skips_weekend():
    from datetime import datetime

    from app.market_hours import NYSE_TZ
    from app.scheduler import next_run

    friday_evening = datetime(2026, 8, 14, 18, 0, tzinfo=NYSE_TZ)  # viernes post-cierre
    target = next_run(friday_evening)
    assert target.weekday() == 0  # lunes
    assert (target.hour, target.minute) == (16, 45)

    tuesday_morning = datetime(2026, 8, 11, 9, 0, tzinfo=NYSE_TZ)
    same_day = next_run(tuesday_morning)
    assert same_day.date() == tuesday_morning.date()

    _ = timedelta  # silencio para linters de imports en refactors futuros
