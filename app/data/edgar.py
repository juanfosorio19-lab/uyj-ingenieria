"""Fundamentales desde SEC EDGAR — gratis, oficial, con fecha de publicación.

La clave de honestidad: cada dato se guarda con su `filed` (fecha en que el
mercado lo CONOCIÓ). Cualquier uso point-in-time filtra por filed <= fecha
de decisión — los resultados del Q1 no existían el 31 de marzo.

La SEC exige un User-Agent identificable (SEC_USER_AGENT en .env) y tolera
~10 req/s; ingerimos con pausa entre símbolos.
"""

import logging
import time
from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Fundamental

log = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# Etiquetas XBRL de ingresos, en orden de preferencia (varían por empresa).
REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
]


def _client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": get_settings().sec_user_agent},
        timeout=60,
        transport=transport,
        follow_redirects=True,
    )


def fetch_cik_map(http: httpx.Client) -> dict[str, int]:
    response = http.get(TICKERS_URL)
    response.raise_for_status()
    return {row["ticker"].upper(): int(row["cik_str"]) for row in response.json().values()}


def extract_annual_revenue(facts: dict) -> list[dict]:
    """Ingresos anuales (10-K) con su fecha de publicación. Puro, testeable."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in REVENUE_TAGS:
        units = gaap.get(tag, {}).get("units", {}).get("USD", [])
        annual = [
            {
                "period_end": date.fromisoformat(row["end"]),
                "value": Decimal(str(row["val"])),
                "filed": date.fromisoformat(row["filed"]),
                "form": row.get("form", ""),
            }
            for row in units
            if row.get("form") == "10-K" and row.get("filed") and row.get("end")
        ]
        if annual:
            # un mismo período puede re-publicarse: nos quedamos con el primer filed
            by_period: dict[date, dict] = {}
            for row in annual:
                current = by_period.get(row["period_end"])
                if current is None or row["filed"] < current["filed"]:
                    by_period[row["period_end"]] = row
            return sorted(by_period.values(), key=lambda r: r["period_end"])
    return []


def ingest_fundamentals(
    session_factory: sessionmaker[Session],
    symbols: list[str],
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Descarga y guarda ingresos anuales para el universo. Idempotente."""
    added, failed = 0, []
    with _client(transport) as http:
        try:
            cik_map = fetch_cik_map(http)
        except Exception:
            log.exception("No se pudo obtener el mapa ticker→CIK de la SEC")
            return "EDGAR inaccesible: no se pudo bajar el mapa de tickers"
        for symbol in symbols:
            cik = cik_map.get(symbol.replace("-", ""))  # BRK-B → BRKB en la SEC
            if cik is None:
                cik = cik_map.get(symbol)
            if cik is None:
                failed.append(symbol)
                continue
            try:
                response = http.get(FACTS_URL.format(cik=cik))
                response.raise_for_status()
                rows = extract_annual_revenue(response.json())
            except Exception:
                log.exception("EDGAR falló para %s", symbol)
                failed.append(symbol)
                continue
            with session_factory() as s:
                existing = {
                    (r.period_end, r.filed)
                    for r in s.scalars(
                        select(Fundamental).where(
                            Fundamental.symbol == symbol,
                            Fundamental.metric == "revenue_annual",
                        )
                    )
                }
                for row in rows:
                    if (row["period_end"], row["filed"]) in existing:
                        continue
                    s.add(
                        Fundamental(
                            symbol=symbol, metric="revenue_annual",
                            period_end=row["period_end"], value=row["value"],
                            filed=row["filed"], form=row["form"],
                        )
                    )
                    added += 1
                s.commit()
            time.sleep(0.12)  # cortesía con la SEC
    msg = f"Fundamentales: {added} filas nuevas"
    if failed:
        msg += f" · sin datos: {', '.join(failed[:10])}"
    return msg


def revenue_growth_yoy(
    session_factory: sessionmaker[Session], symbol: str, as_of: date
) -> float | None:
    """Crecimiento anual de ingresos usando SOLO datos publicados hasta as_of."""
    with session_factory() as s:
        rows = s.scalars(
            select(Fundamental)
            .where(
                Fundamental.symbol == symbol,
                Fundamental.metric == "revenue_annual",
                Fundamental.filed <= as_of,
            )
            .order_by(Fundamental.period_end.desc())
        ).all()
    if len(rows) < 2:
        return None
    latest = rows[0]
    for prev in rows[1:]:
        gap = (latest.period_end - prev.period_end).days
        if 300 <= gap <= 430 and Decimal(prev.value) != 0:
            return float(Decimal(latest.value) / Decimal(prev.value) - 1)
    return None
