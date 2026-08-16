"""Broker simulado respaldado en base de datos.

Cumple los tres contratos que después heredan los brokers reales:
- idempotencia: la misma `idempotency_key` jamás ejecuta dos veces;
- kill switch: con órdenes deshabilitadas, nada se ejecuta;
- ledger tributario: cada compra abre un lote FIFO y cada venta lo cierra.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.brokers.base import OrderRejected, OrderResult, PositionInfo
from app.market_hours import is_nyse_open
from app.models import (
    Account,
    Execution,
    FxRate,
    Order,
    Position,
    SystemFlag,
    TaxLot,
    TaxLotClosing,
)

# Precios de referencia estáticos: suficientes para la fase 0.
# La fase 1 los reemplaza por datos de mercado reales.
_STUB_PRICES = {
    "AAPL": Decimal("230.00"),
    "MSFT": Decimal("420.00"),
    "NVDA": Decimal("120.00"),
    "SPY": Decimal("560.00"),
}
_DEFAULT_PRICE = Decimal("100.00")


class PaperAdapter:
    name = "paper"

    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    # -- lecturas -----------------------------------------------------------

    def get_cash(self) -> Decimal:
        with self._sf() as s:
            account = s.get(Account, 1)
            return Decimal(account.cash_usd) if account else Decimal(0)

    def get_positions(self) -> list[PositionInfo]:
        with self._sf() as s:
            rows = s.scalars(select(Position).order_by(Position.symbol)).all()
            return [
                PositionInfo(p.symbol, Decimal(p.qty), Decimal(p.avg_price_usd)) for p in rows
            ]

    def get_order_status(self, client_order_id: str) -> str | None:
        with self._sf() as s:
            order = s.scalar(select(Order).where(Order.client_order_id == client_order_id))
            return order.status if order else None

    def is_market_open(self) -> bool:
        return is_nyse_open()

    # -- escritura ----------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: Decimal,
        idempotency_key: str,
        price: Decimal | None = None,
    ) -> OrderResult:
        symbol = symbol.upper().strip()
        side = side.lower().strip()
        qty = Decimal(qty)
        if side not in ("buy", "sell"):
            raise OrderRejected(f"Side inválido: {side!r} (buy|sell)")
        if qty <= 0:
            raise OrderRejected("La cantidad debe ser positiva")

        with self._sf() as s:
            flag = s.get(SystemFlag, "orders_enabled")
            if flag is not None and flag.value != "true":
                raise OrderRejected("Kill switch activo: órdenes deshabilitadas")

            existing = s.scalar(select(Order).where(Order.client_order_id == idempotency_key))
            if existing is not None:
                return OrderResult(
                    client_order_id=existing.client_order_id,
                    symbol=existing.symbol,
                    side=existing.side,
                    qty=Decimal(existing.qty),
                    fill_price_usd=Decimal(existing.price_usd),
                    status=existing.status,
                    duplicate=True,
                )

            fill_price = Decimal(price) if price is not None else _STUB_PRICES.get(
                symbol, _DEFAULT_PRICE
            )
            if fill_price <= 0:
                raise OrderRejected("El precio debe ser positivo")

            if side == "buy":
                self._execute_buy(s, symbol, qty, fill_price)
            else:
                self._execute_sell(s, symbol, qty, fill_price)

            order = Order(
                client_order_id=idempotency_key,
                symbol=symbol,
                side=side,
                qty=qty,
                price_usd=fill_price,
                status="filled",
            )
            s.add(order)
            s.flush()
            s.add(
                Execution(
                    order_id=order.id,
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    decision_price_usd=fill_price,  # en paper, decisión == fill
                    fill_price_usd=fill_price,
                    slippage_pct=Decimal(0),
                )
            )
            s.commit()

        return OrderResult(
            client_order_id=idempotency_key,
            symbol=symbol,
            side=side,
            qty=qty,
            fill_price_usd=fill_price,
            status="filled",
        )

    # -- internos -----------------------------------------------------------

    def _execute_buy(self, s: Session, symbol: str, qty: Decimal, price: Decimal) -> None:
        account = s.get(Account, 1)
        cost = qty * price
        if account is None or Decimal(account.cash_usd) < cost:
            available = Decimal(account.cash_usd) if account else Decimal(0)
            raise OrderRejected(f"Caja insuficiente: necesitas {cost:.2f}, hay {available:.2f}")
        account.cash_usd = Decimal(account.cash_usd) - cost

        position = s.scalar(select(Position).where(Position.symbol == symbol))
        if position is None:
            s.add(Position(symbol=symbol, qty=qty, avg_price_usd=price))
        else:
            old_qty = Decimal(position.qty)
            old_avg = Decimal(position.avg_price_usd)
            position.qty = old_qty + qty
            position.avg_price_usd = (old_qty * old_avg + qty * price) / (old_qty + qty)
            position.updated_at = datetime.now(UTC)

        today = datetime.now(UTC).date()
        fx = s.scalar(select(FxRate).order_by(FxRate.date.desc()).limit(1))
        s.add(
            TaxLot(
                symbol=symbol,
                open_date=today,
                open_qty=qty,
                open_price_usd=price,
                open_fx_clp=fx.clp_per_usd if fx else None,
                remaining_qty=qty,
            )
        )

    def _execute_sell(self, s: Session, symbol: str, qty: Decimal, price: Decimal) -> None:
        position = s.scalar(select(Position).where(Position.symbol == symbol))
        if position is None or Decimal(position.qty) < qty:
            held = Decimal(position.qty) if position else Decimal(0)
            raise OrderRejected(f"Posición insuficiente en {symbol}: tienes {held}, vendes {qty}")

        remaining = Decimal(position.qty) - qty
        if remaining == 0:
            s.delete(position)
        else:
            position.qty = remaining
            position.updated_at = datetime.now(UTC)

        account = s.get(Account, 1)
        account.cash_usd = Decimal(account.cash_usd) + qty * price

        self._close_lots_fifo(s, symbol, qty, price)

    def _close_lots_fifo(self, s: Session, symbol: str, qty: Decimal, price: Decimal) -> None:
        today = datetime.now(UTC).date()
        fx = s.scalar(select(FxRate).order_by(FxRate.date.desc()).limit(1))
        fx_value = fx.clp_per_usd if fx else None
        lots = s.scalars(
            select(TaxLot)
            .where(TaxLot.symbol == symbol, TaxLot.remaining_qty > 0)
            .order_by(TaxLot.open_date, TaxLot.id)
        ).all()
        remaining = qty
        for lot in lots:
            if remaining <= 0:
                break
            take = min(Decimal(lot.remaining_qty), remaining)
            lot.remaining_qty = Decimal(lot.remaining_qty) - take
            gain_usd = (price - Decimal(lot.open_price_usd)) * take
            gain_clp = None
            if fx_value is not None and lot.open_fx_clp is not None:
                gain_clp = (
                    price * Decimal(fx_value) - Decimal(lot.open_price_usd) * Decimal(lot.open_fx_clp)
                ) * take
            s.add(
                TaxLotClosing(
                    lot_id=lot.id,
                    close_date=today,
                    qty=take,
                    close_price_usd=price,
                    close_fx_clp=fx_value,
                    realized_gain_usd=gain_usd,
                    realized_gain_clp=gain_clp,
                    holding_days=(today - lot.open_date).days,
                )
            )
            remaining -= take
