"""Reporte diario: top movers, benchmark, portafolio, dólar y salud de ingesta.

Es el entregable visible de la fase 1: este texto llega solo a Telegram
todas las mañanas (post-cierre NYSE del día anterior).
"""

from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.brokers.paper import PaperAdapter
from app.config import get_settings
from app.models import FxRate, PriceBar
from app.universe import BENCHMARK


def _pct(new: Decimal, old: Decimal) -> Decimal:
    if old == 0:
        return Decimal(0)
    return (new - old) / old * 100


def build_daily_report(session_factory: sessionmaker[Session]) -> str:
    with session_factory() as s:
        last_date = s.scalar(select(func.max(PriceBar.date)))
        if last_date is None:
            return "📊 Sin datos de mercado todavía. Corre la ingesta: python -m app.jobs ingest"
        prev_date = s.scalar(select(func.max(PriceBar.date)).where(PriceBar.date < last_date))

        rows = s.execute(
            select(PriceBar.symbol, PriceBar.date, PriceBar.close).where(
                PriceBar.date.in_([d for d in (last_date, prev_date) if d is not None])
            )
        ).all()

    closes: dict[str, dict] = {}
    for symbol, day, close in rows:
        closes.setdefault(symbol, {})[day] = Decimal(close)

    changes: list[tuple[str, Decimal]] = []
    stale: list[str] = []
    for symbol, by_date in closes.items():
        if last_date in by_date and prev_date in by_date:
            changes.append((symbol, _pct(by_date[last_date], by_date[prev_date])))
        elif last_date not in by_date:
            stale.append(symbol)

    changes.sort(key=lambda item: item[1], reverse=True)
    benchmark = next((c for c in changes if c[0] == BENCHMARK), None)
    movers = [c for c in changes if c[0] != BENCHMARK]
    top_up = [c for c in movers[:5] if c[1] > 0]
    top_down = [c for c in reversed(movers[-5:]) if c[1] < 0]

    lines = [f"📊 Resumen diario — cierre {last_date}"]
    if top_up:
        lines.append("🔼 " + " · ".join(f"{s} +{p:.1f}%" for s, p in top_up))
    if top_down:
        lines.append("🔽 " + " · ".join(f"{s} {p:.1f}%" for s, p in top_down))
    if benchmark:
        lines.append(f"🎯 {BENCHMARK}: {benchmark[1]:+.1f}%")

    adapter = PaperAdapter(session_factory)
    positions = adapter.get_positions()
    if positions:
        detail = ", ".join(f"{p.symbol} {p.qty:g}" for p in positions)
        lines.append(f"💼 Caja USD {adapter.get_cash():,.2f} · Posiciones: {detail}")
    else:
        lines.append(f"💼 Caja USD {adapter.get_cash():,.2f} · sin posiciones")

    with session_factory() as s:
        fx = s.scalar(select(FxRate).order_by(FxRate.date.desc()).limit(1))
    if fx:
        lines.append(f"💱 Dólar observado: ${Decimal(fx.clp_per_usd):,.2f} ({fx.date})")

    total = len(closes)
    lines.append(
        f"🩺 Ingesta: {total - len(stale)}/{total} símbolos al día"
        + (f" · atrasados: {', '.join(sorted(stale)[:8])}" if stale else "")
    )
    return "\n".join(lines)


def send_telegram_document(path, caption: str = "") -> bool:
    """Envía un archivo (p. ej. el HTML del backtest) al chat configurado."""
    settings = get_settings()
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id.strip().strip('"').strip("'")
    if not token or not chat_id:
        print(f"(Documento no enviado, falta config de Telegram: {path})")
        return False
    with open(path, "rb") as fh:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption[:1000]},
            files={"document": fh},
            timeout=60,
        )
    response.raise_for_status()
    return True


def send_telegram_message(text: str) -> bool:
    """Envía por la API HTTP del bot. Sin token/chat configurados, imprime y sigue."""
    settings = get_settings()
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id.strip().strip('"').strip("'")
    if not token or not chat_id:
        print(text)
        print("(TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID no configurados: impreso en consola)")
        return False
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    response.raise_for_status()
    return True
