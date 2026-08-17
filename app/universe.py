"""Universo de símbolos a seguir.

La lista sembrada es el punto de partida (grandes capitalizaciones líquidas
de EE.UU. + SPY como benchmark). La tabla `universe` guarda vigencias
(valid_from/valid_to) para poder reconstruir el universo en cualquier fecha.

TODO fase 2 (bloqueante para el backtest): cargar constituyentes HISTÓRICOS.
Backtestear con la lista de hoy hacia el pasado es survivorship bias.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import UniverseMember

BENCHMARK = "SPY"

DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "BRK-B", "JPM",
    "V", "MA", "UNH", "XOM", "JNJ", "WMT", "PG", "HD", "COST", "ORCL",
    "LLY", "ABBV", "BAC", "KO", "PEP", "CRM", "CSCO", "AMD", "NFLX", "ADBE",
    "TMO", "MCD", "ACN", "INTC", "IBM", "QCOM", "TXN", "CAT", "GE", "DIS",
    "VZ", "PFE", "MRK", "NKE", "UNP", "LOW", "GS", "MS", "RTX", "HON",
]


def ensure_universe(session_factory: sessionmaker[Session]) -> list[str]:
    """Siembra el universo si la tabla está vacía; devuelve los símbolos vigentes."""
    today = datetime.now(UTC).date()
    with session_factory() as s:
        active = s.scalars(
            select(UniverseMember.symbol).where(UniverseMember.valid_to.is_(None))
        ).all()
        if active:
            return sorted(set(active) | {BENCHMARK})
        for symbol in [*DEFAULT_UNIVERSE, BENCHMARK]:
            s.add(UniverseMember(symbol=symbol, valid_from=today, valid_to=None))
        s.commit()
        return sorted([*DEFAULT_UNIVERSE, BENCHMARK])
