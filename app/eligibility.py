"""Máscaras de elegibilidad point-in-time para el backtest.

Un símbolo es candidato en la fecha d solo si:
1. era miembro del universo en d (si hay historia de constituyentes cargada), y
2. su último crecimiento de ingresos PUBLICADO hasta d no era negativo
   (si hay fundamentales cargados; sin dato → no se excluye).

Las máscaras se construyen desde tablas con vigencias/fechas de publicación:
cero look-ahead por construcción.
"""

from datetime import date, datetime

import pandas as pd


def _as_date(value) -> date:
    """El índice puede traer Timestamps (pandas) o dates (DB): normaliza."""
    return value.date() if isinstance(value, datetime | pd.Timestamp) else value
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.data.edgar import revenue_growth_yoy
from app.models import Fundamental, UniverseMember


def membership_mask(
    session_factory: sessionmaker[Session], index: pd.Index, symbols: list[str]
) -> pd.DataFrame | None:
    """Máscara de pertenencia. None si no hay historia real cargada.

    La lista sembrada (todas las filas sin valid_to) no es historia: aplicarla
    hacia el pasado sería fingir precisión. Solo actúa cuando se cargó un CSV
    de constituyentes históricos (hay filas con valid_to).
    """
    with session_factory() as s:
        rows = s.scalars(select(UniverseMember)).all()
    if not rows or not any(r.valid_to is not None for r in rows):
        return None
    dates = [_as_date(d) for d in index]
    mask = pd.DataFrame(False, index=index, columns=symbols)
    for row in rows:
        if row.symbol not in mask.columns:
            continue
        start = row.valid_from
        end = row.valid_to or date.max
        in_range = [(d >= start) and (d <= end) for d in dates]
        mask.loc[in_range, row.symbol] |= True
    return mask


def quality_mask(
    session_factory: sessionmaker[Session], index: pd.Index, symbols: list[str]
) -> pd.DataFrame | None:
    """Filtro de calidad: crecimiento de ingresos publicado >= 0. None sin datos."""
    with session_factory() as s:
        have_data = {
            row
            for row in s.scalars(
                select(Fundamental.symbol).where(Fundamental.metric == "revenue_annual")
            )
        }
    if not have_data:
        return None
    dates = [_as_date(d) for d in index]
    mask = pd.DataFrame(True, index=index, columns=symbols)
    # evaluar una vez al mes basta: el dato anual cambia con cada 10-K
    month_starts = [
        d for i, d in enumerate(dates) if i == 0 or d.month != dates[i - 1].month
    ]
    for symbol in symbols:
        if symbol not in have_data:
            continue  # sin fundamentales => no se excluye
        current = True
        starts = iter(month_starts)
        next_start = next(starts, None)
        values = []
        for d in dates:
            if next_start is not None and d >= next_start:
                growth = revenue_growth_yoy(session_factory, symbol, as_of=d)
                current = growth is None or growth >= 0
                next_start = next(starts, None)
            values.append(current)
        mask[symbol] = values
    return mask


def build_eligibility(
    session_factory: sessionmaker[Session], closes: pd.DataFrame
) -> pd.DataFrame | None:
    symbols = list(closes.columns)
    membership = membership_mask(session_factory, closes.index, symbols)
    quality = quality_mask(session_factory, closes.index, symbols)
    if membership is None and quality is None:
        return None
    combined = pd.DataFrame(True, index=closes.index, columns=symbols)
    if membership is not None:
        combined &= membership
    if quality is not None:
        combined &= quality
    return combined
