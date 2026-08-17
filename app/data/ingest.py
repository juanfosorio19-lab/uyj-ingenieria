"""Ingesta de precios OHLCV diarios.

Fuente intercambiable (Protocol): yfinance en desarrollo/paper; en fase 2+
se puede sumar EODHD/FMP sin tocar el resto. La ingesta es incremental e
idempotente: parte donde quedó y jamás duplica una barra.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import PriceBar

log = logging.getLogger(__name__)

BACKFILL_DAYS = 3 * 365


@dataclass
class Bar:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class PriceSource(Protocol):
    def fetch(self, symbol: str, start: date, end: date) -> list[Bar]: ...


class YFinanceSource:
    """Fuente gratuita para desarrollo. No apta para producción seria."""

    def fetch(self, symbol: str, start: date, end: date) -> list[Bar]:
        import yfinance as yf  # import perezoso: pesado y solo se usa aquí

        frame = yf.Ticker(symbol).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),  # yfinance excluye el fin
            interval="1d",
            auto_adjust=False,
        )
        bars: list[Bar] = []
        for idx, row in frame.iterrows():
            if any(row.get(col) is None for col in ("Open", "High", "Low", "Close")):
                continue
            bars.append(
                Bar(
                    date=idx.date(),
                    open=Decimal(str(round(row["Open"], 6))),
                    high=Decimal(str(round(row["High"], 6))),
                    low=Decimal(str(round(row["Low"], 6))),
                    close=Decimal(str(round(row["Close"], 6))),
                    volume=int(row.get("Volume") or 0),
                )
            )
        return bars


@dataclass
class IngestSummary:
    bars_added: int = 0
    symbols_ok: list[str] = field(default_factory=list)
    symbols_failed: list[str] = field(default_factory=list)
    last_date: date | None = None

    def one_liner(self) -> str:
        msg = f"{len(self.symbols_ok)} símbolos al día, {self.bars_added} barras nuevas"
        if self.symbols_failed:
            msg += f", FALLARON: {', '.join(self.symbols_failed)}"
        return msg


def ingest_symbol(
    session_factory: sessionmaker[Session],
    source: PriceSource,
    symbol: str,
    today: date | None = None,
) -> int:
    """Trae barras desde la última guardada (o 3 años atrás). Devuelve barras nuevas."""
    today = today or datetime.now(UTC).date()
    with session_factory() as s:
        last = s.scalar(select(func.max(PriceBar.date)).where(PriceBar.symbol == symbol))
        start = (last + timedelta(days=1)) if last else today - timedelta(days=BACKFILL_DAYS)
        if start > today:
            return 0
        bars = source.fetch(symbol, start, today)
        existing = set(
            s.scalars(
                select(PriceBar.date).where(
                    PriceBar.symbol == symbol, PriceBar.date >= start
                )
            ).all()
        )
        added = 0
        for bar in bars:
            if bar.date in existing or bar.date > today:
                continue
            s.add(
                PriceBar(
                    symbol=symbol,
                    date=bar.date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
            )
            added += 1
        s.commit()
        return added


def ingest_universe(
    session_factory: sessionmaker[Session],
    source: PriceSource,
    symbols: list[str],
    today: date | None = None,
) -> IngestSummary:
    summary = IngestSummary()
    for symbol in symbols:
        try:
            summary.bars_added += ingest_symbol(session_factory, source, symbol, today=today)
            summary.symbols_ok.append(symbol)
        except Exception:  # una acción caída no detiene el resto
            log.exception("Ingesta falló para %s", symbol)
            summary.symbols_failed.append(symbol)
    with session_factory() as s:
        summary.last_date = s.scalar(select(func.max(PriceBar.date)))
    return summary
