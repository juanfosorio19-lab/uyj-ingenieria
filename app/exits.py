"""Reglas de salida deterministas — la IA NO participa en ninguna.

Orden de precedencia del plan (sección 5), sin excepciones ni consultas:
1. Stop duro (−20% desde entrada) → vender todo.
2. Invalidador de tesis activado → vender todo.
3. Horizonte cumplido → vender todo.
4. Concentración excedida → recortar al límite.
5. Todo lo demás → mantener.

La IA formó la tesis y los invalidadores EN LA ENTRADA; la salida es
mecánica. Esto elimina la clase completa de fallos donde un modelo
racionaliza mantener una posición perdedora.
"""

import logging
import operator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.backtest import load_close_matrix
from app.brokers.base import OrderRejected, PositionInfo
from app.models import Thesis
from app.scoring import LOOKBACK, SKIP, momentum_scores
from app.trade import sync_positions

log = logging.getLogger(__name__)

HARD_STOP = -0.20
MAX_POSITION_PCT = 0.10

_OPS = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge,
        "==": operator.eq}


@dataclass
class ExitAction:
    symbol: str
    qty: Decimal  # cuánto vender
    rule: str  # stop_duro | invalidador | horizonte | concentracion
    reason: str
    sells_all: bool


def evaluate_exit(
    position: PositionInfo,
    thesis: Thesis | None,
    *,
    current_price: Decimal,
    momentum: float | None,
    today: date,
    portfolio_value: Decimal,
    max_position_pct: float = MAX_POSITION_PCT,
    hard_stop: float = HARD_STOP,
) -> ExitAction | None:
    """Función pura: aplica las 5 reglas en orden y devuelve la primera que gatilla."""
    entry = Decimal(position.avg_price_usd)
    if entry <= 0 or current_price <= 0:
        return None
    price_vs_entry = float(current_price / entry - 1)

    # 1. Stop duro: sin excepción, con o sin tesis.
    if price_vs_entry <= hard_stop:
        return ExitAction(
            position.symbol, Decimal(position.qty), "stop_duro",
            f"precio {price_vs_entry:+.1%} vs entrada (límite {hard_stop:.0%})", True,
        )

    days_held = (today - thesis.created_at.date()).days if thesis is not None else None

    # 2. Invalidadores de tesis (solo métricas evaluables mecánicamente).
    if thesis is not None:
        metrics: dict[str, float | None] = {
            "price_vs_entry": price_vs_entry,
            "momentum_6m1m": momentum,
            "days_held": float(days_held) if days_held is not None else None,
        }
        for inv in thesis.invalidators or []:
            metric_value = metrics.get(inv.get("metric"))
            op = _OPS.get(inv.get("op", ""))
            threshold = inv.get("value")
            if metric_value is None or op is None or not isinstance(threshold, int | float):
                continue  # métrica no evaluable aún (p. ej. fundamentales): se ignora
            if op(metric_value, float(threshold)):
                return ExitAction(
                    position.symbol, Decimal(position.qty), "invalidador",
                    f"{inv['metric']} = {metric_value:.3f} cumple {inv['op']} {threshold}", True,
                )

        # 3. Horizonte cumplido.
        if days_held is not None and days_held > thesis.target_horizon_days:
            return ExitAction(
                position.symbol, Decimal(position.qty), "horizonte",
                f"{days_held} días en cartera > horizonte {thesis.target_horizon_days}", True,
            )

    # 4. Concentración: recortar al límite.
    value = Decimal(position.qty) * current_price
    if portfolio_value > 0:
        pct = float(value / portfolio_value)
        if pct > max_position_pct + 1e-9:
            excess_value = value - portfolio_value * Decimal(str(max_position_pct))
            trim_qty = (excess_value / current_price).quantize(
                Decimal("0.0001"), rounding=ROUND_DOWN
            )
            if trim_qty > 0:
                return ExitAction(
                    position.symbol, trim_qty, "concentracion",
                    f"posición {pct:.0%} > límite {max_position_pct:.0%}: recorte", False,
                )

    return None  # 5. mantener


def check_and_execute_exits(session_factory: sessionmaker[Session], adapter) -> list[str]:
    """Evalúa cada posición y ejecuta las salidas que correspondan."""
    positions = adapter.get_positions()
    if not positions:
        return []

    closes = load_close_matrix(session_factory)
    today = datetime.now(UTC).date()
    cash = Decimal(adapter.get_cash())

    def price_of(pos: PositionInfo) -> Decimal | None:
        if pos.current_price_usd:
            return Decimal(pos.current_price_usd)
        if not closes.empty and pos.symbol in closes.columns:
            return Decimal(str(closes[pos.symbol].dropna().iloc[-1]))
        return None

    prices = {p.symbol: price_of(p) for p in positions}
    portfolio_value = cash + sum(
        (Decimal(p.qty) * prices[p.symbol] for p in positions if prices[p.symbol]),
        Decimal(0),
    )

    messages: list[str] = []
    for pos in positions:
        current = prices[pos.symbol]
        if current is None:
            log.warning("Sin precio para %s: no se evalúa salida", pos.symbol)
            continue

        momentum = None
        if not closes.empty and pos.symbol in closes.columns:
            series = closes[[pos.symbol]].dropna()
            if len(series) > LOOKBACK + SKIP:
                score = momentum_scores(series, at=len(series) - 1)
                momentum = float(score[pos.symbol]) if not score.empty else None

        with session_factory() as s:
            thesis = s.scalar(
                select(Thesis)
                .where(Thesis.symbol == pos.symbol, Thesis.status == "open")
                .order_by(Thesis.created_at.desc())
                .limit(1)
            )

        action = evaluate_exit(
            pos, thesis, current_price=current, momentum=momentum,
            today=today, portfolio_value=portfolio_value,
        )
        if action is None:
            continue

        key = f"exit-{today}-{action.symbol}-{action.rule}"
        try:
            result = adapter.place_order(action.symbol, "sell", action.qty, key, price=current)
        except OrderRejected as exc:
            messages.append(f"🛑 Venta defensiva de {action.symbol} RECHAZADA: {exc}")
            continue

        if thesis is not None and action.sells_all:
            with session_factory() as s:
                row = s.get(Thesis, thesis.id)
                if row is not None:
                    row.status = "closed"
                    s.commit()

        dup = " (reintento idempotente)" if result.duplicate else ""
        verb = "VENDIDA toda la posición" if action.sells_all else f"RECORTADA en {action.qty:g}"
        messages.append(
            f"🛡️ Salida defensiva [{action.rule}]: {action.symbol} {verb}{dup}\n"
            f"Razón: {action.reason} · estado: {result.status}"
        )

    if messages:
        sync_positions(session_factory, adapter)
    return messages
