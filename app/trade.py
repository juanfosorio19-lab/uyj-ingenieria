"""Ciclo de trading (fase 4): reconciliar → analizar → validar riesgo → ejecutar.

Orden inviolable del plan: la reconciliación va PRIMERO. Si el estado local
y el broker divergen, el sistema se detiene solo (kill switch) y avisa —
nunca opera sobre estado asumido.
"""

import logging
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.brokers.base import OrderRejected
from app.controls import set_orders_enabled
from app.llm.analyst import AnalystClient, analyze
from app.models import Position, PriceBar, Reconciliation
from app.risk import evaluate_from_db

log = logging.getLogger(__name__)

QTY_TOLERANCE = 1e-4


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
