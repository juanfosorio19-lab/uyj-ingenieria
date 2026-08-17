"""Ciclo de trading (fase 4): reconciliar → analizar → validar riesgo → ejecutar.

Orden inviolable del plan: la reconciliación va PRIMERO. Si el estado local
y el broker divergen, el sistema se detiene solo (kill switch) y avisa —
nunca opera sobre estado asumido.
"""

import logging
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.brokers.base import OrderRejected
from app.controls import heartbeat_age_seconds, set_orders_enabled
from app.llm.analyst import AnalystClient, analyze
from app.models import PortfolioSnapshot, Position, PriceBar, Reconciliation
from app.risk import evaluate_from_db

log = logging.getLogger(__name__)

QTY_TOLERANCE = 1e-4
DMS_MAX_AGE_SECONDS = 45 * 60  # el monitor late cada 15 min; 45 min sin latido = caído


def reconcile(session_factory: sessionmaker[Session], adapter) -> bool:
    """Compara broker vs estado local. Divergencia => HALT automático."""
    broker_positions = {p.symbol: float(p.qty) for p in adapter.get_positions()}
    with session_factory() as s:
        local_positions = {
            p.symbol: float(p.qty) for p in s.scalars(select(Position)).all()
        }

    if adapter.name == "paper":
        ok = True  # paper comparte la misma base: no puede divergir
    else:
        symbols = set(broker_positions) | set(local_positions)
        ok = all(
            abs(broker_positions.get(sym, 0.0) - local_positions.get(sym, 0.0))
            <= QTY_TOLERANCE
            for sym in symbols
        )

    with session_factory() as s:
        s.add(
            Reconciliation(
                broker=adapter.name,
                status="ok" if ok else "divergent",
                details={"broker": broker_positions, "local": local_positions},
            )
        )
        s.commit()

    if not ok:
        set_orders_enabled(
            session_factory, False, actor="reconciliation",
            reason=f"divergencia broker({adapter.name}) vs local",
        )
        log.error("Reconciliación divergente: HALT. broker=%s local=%s",
                  broker_positions, local_positions)
    return ok


def sync_positions(session_factory: sessionmaker[Session], adapter) -> None:
    """El broker externo es la verdad: el espejo local se rehace desde él."""
    if adapter.name == "paper":
        return
    broker_positions = adapter.get_positions()
    with session_factory() as s:
        for row in s.scalars(select(Position)).all():
            s.delete(row)
        for p in broker_positions:
            s.add(Position(symbol=p.symbol, qty=p.qty, avg_price_usd=p.avg_price_usd))
        s.commit()


def _last_close(session_factory, symbol: str) -> Decimal | None:
    with session_factory() as s:
        bar = s.scalar(
            select(PriceBar)
            .where(PriceBar.symbol == symbol)
            .order_by(PriceBar.date.desc())
            .limit(1)
        )
        return Decimal(bar.close) if bar else None


def _last_data_date(session_factory) -> str:
    with session_factory() as s:
        return str(s.scalar(select(func.max(PriceBar.date))))


def snapshot_portfolio(session_factory: sessionmaker[Session], adapter) -> None:
    """Foto diaria de caja/posiciones/equity — la curva del dashboard."""
    cash = Decimal(adapter.get_cash())
    positions_value = sum(
        (
            Decimal(p.qty) * Decimal(p.current_price_usd or p.avg_price_usd)
            for p in adapter.get_positions()
        ),
        Decimal(0),
    )
    today = datetime.now(UTC).date()
    with session_factory() as s:
        row = s.get(PortfolioSnapshot, today)
        if row is None:
            row = PortfolioSnapshot(date=today, cash_usd=0, positions_value_usd=0, equity_usd=0)
            s.add(row)
        row.cash_usd = cash
        row.positions_value_usd = positions_value
        row.equity_usd = cash + positions_value
        s.commit()


def trade_once(
    session_factory: sessionmaker[Session], adapter, client: AnalystClient | None = None
) -> str:
    """Un ciclo completo de decisión→ejecución. Devuelve el mensaje para Telegram."""
    if not reconcile(session_factory, adapter):
        return (
            "🛑 HALT: el estado local y el broker divergen. Órdenes deshabilitadas.\n"
            "Revisa /status y usa /resume cuando esté explicado."
        )

    outcome = analyze(session_factory, client=client)
    if outcome.status == "no_data":
        return "🤖 Sin datos suficientes para decidir (corre la ingesta)."
    if outcome.status == "rejected_schema":
        return "🤖 Propuesta RECHAZADA por formato inválido (auditada, no ejecutada)."
    if outcome.status == "error":
        return "🤖 El analista falló hoy; queda registrado. Sin operación."

    proposal = outcome.proposal
    if proposal.action == "hold":
        return f"🤖 Decisión del día: MANTENER.\nRazón: {proposal.thesis}"

    verdict = evaluate_from_db(session_factory, proposal, adapter=adapter)
    invalidators = "; ".join(f"{i.metric} {i.op} {i.value}" for i in proposal.invalidators)
    header = (
        f"🤖 Decisión: COMPRAR {proposal.symbol} ({proposal.max_position_pct:.0%})\n"
        f"Tesis: {proposal.thesis}\nInvalidadores: {invalidators}\n"
        f"🛡️ Risk Engine: {verdict.summary}"
    )
    if not verdict.approved:
        return header + "\n→ NO ejecutada."

    # Dead man's switch: si el monitor se armó alguna vez y dejó de latir,
    # no se abren posiciones nuevas (y se apaga el flag global).
    age = heartbeat_age_seconds(session_factory, key="monitor")
    if age is not None and age > DMS_MAX_AGE_SECONDS:
        set_orders_enabled(
            session_factory, False, actor="dead-man-switch",
            reason=f"monitor sin latido hace {age / 60:.0f} min",
        )
        return header + (
            f"\n🛑 Dead man's switch: el monitor lleva {age / 60:.0f} min sin latir. "
            "Órdenes deshabilitadas; revisa el proceso y usa /resume."
        )

    price = _last_close(session_factory, proposal.symbol)
    if price is None or price <= 0:
        return header + "\n→ NO ejecutada: sin precio de referencia."

    cash = Decimal(adapter.get_cash())
    positions_value = sum(
        (Decimal(p.qty) * Decimal(p.avg_price_usd) for p in adapter.get_positions()),
        Decimal(0),
    )
    portfolio_value = cash + positions_value
    notional = portfolio_value * Decimal(str(proposal.max_position_pct))
    qty = (notional / price).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
    if qty <= 0:
        return header + "\n→ NO ejecutada: monto demasiado chico."

    idempotency_key = f"trade-{_last_data_date(session_factory)}-{proposal.symbol}-buy"
    try:
        result = adapter.place_order(
            proposal.symbol, "buy", qty, idempotency_key, price=price
        )
    except OrderRejected as exc:
        return header + f"\n→ Broker la rechazó: {exc}"

    sync_positions(session_factory, adapter)
    if result.duplicate:
        return header + "\n→ Ya estaba ejecutada hoy (reintento idempotente, sin duplicar)."
    fill = f" @ USD {result.fill_price_usd:,.2f}" if result.fill_price_usd else ""
    return (
        header
        + f"\n✅ EJECUTADA en {adapter.name}: {result.qty:g} {result.symbol}{fill} "
        f"(estado: {result.status})"
    )
