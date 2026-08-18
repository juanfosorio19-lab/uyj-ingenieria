"""Dólar observado (CLP/USD) — insumo del ledger tributario.

Fuente: mindicador.cl (gratis, sin API key). Falla con gracia: si no hay
red o el servicio no responde, se registra y se sigue; el ledger guarda
NULL y se puede rellenar después.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.models import FxRate

log = logging.getLogger(__name__)

MINDICADOR_URL = "https://mindicador.cl/api/dolar"


def parse_mindicador(payload: dict) -> tuple[date, Decimal] | None:
    """Extrae (fecha, valor) del JSON de mindicador.cl. None si viene vacío."""
    serie = payload.get("serie") or []
    if not serie:
        return None
    first = serie[0]
    day = datetime.fromisoformat(first["fecha"]).date()
    return day, Decimal(str(first["valor"]))


def update_fx_rate(session_factory: sessionmaker[Session]) -> tuple[date, Decimal] | None:
    """Consulta el dólar observado del día y lo guarda (idempotente)."""
    try:
        response = httpx.get(MINDICADOR_URL, timeout=20)
        response.raise_for_status()
        parsed = parse_mindicador(response.json())
    except Exception:
        log.exception("No se pudo obtener el dólar observado")
        return None
    if parsed is None:
        return None
    day, value = parsed
    with session_factory() as s:
        if s.get(FxRate, day) is None:
            s.add(FxRate(date=day, clp_per_usd=value))
            s.commit()
    return day, value
