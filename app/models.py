"""Esquema completo desde el día 1.

Aunque la fase 0 solo usa una parte, las tablas tributarias y de auditoría
(`tax_lots`, `executions`, `reconciliations`, `theses`, `kill_switch_events`,
`ai_decisions`) existen desde ahora: cuestan lo mismo hoy que después, y
después es tarde.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True)
    cash_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    avg_price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    side: Mapped[str] = mapped_column(String(4))  # buy | sell
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(16))  # filled | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Execution(Base):
    """Calidad de ejecución: precio de decisión vs. fill (slippage)."""

    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(12))
    side: Mapped[str] = mapped_column(String(4))
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    decision_price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    fill_price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    slippage_pct: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TaxLot(Base):
    """Lote tributario FIFO abierto en cada compra (insumo DJ 1929)."""

    __tablename__ = "tax_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    open_date: Mapped[date] = mapped_column(Date)
    open_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    open_price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    open_fx_clp: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    method: Mapped[str] = mapped_column(String(8), default="FIFO")


class TaxLotClosing(Base):
    """Cierre (total o parcial) de un lote: cada venta genera uno o más."""

    __tablename__ = "tax_lot_closings"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("tax_lots.id"), index=True)
    close_date: Mapped[date] = mapped_column(Date)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close_price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close_fx_clp: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    realized_gain_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    realized_gain_clp: Mapped[Decimal | None] = mapped_column(Numeric(18, 0), nullable=True)
    holding_days: Mapped[int] = mapped_column()


class PriceBar(Base):
    """OHLCV diario por símbolo (fase 1)."""

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("symbol", "date", name="uq_prices_symbol_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger, default=0)


class UniverseMember(Base):
    """Universo de símbolos con vigencia (point-in-time).

    `valid_from`/`valid_to` permiten reconstruir el universo en cualquier
    fecha. TODO fase 2: cargar constituyentes históricos reales antes del
    backtest (la lista sembrada parte hoy, no sirve para mirar el pasado).
    """

    __tablename__ = "universe"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class FxRate(Base):
    """Dólar observado por fecha (conversión CLP para el ledger tributario)."""

    __tablename__ = "fx_rates"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    clp_per_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4))


class Reconciliation(Base):
    """Snapshot estado interno vs. broker. Divergencia => HALT (fase 4)."""

    __tablename__ = "reconciliations"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    broker: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16))  # ok | divergent
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class Thesis(Base):
    """Tesis falsable por posición, con invalidadores medibles (fase 3)."""

    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    thesis: Mapped[str] = mapped_column(Text)
    invalidators: Mapped[list] = mapped_column(JSON, default=list)
    target_horizon_days: Mapped[int] = mapped_column(default=90)
    max_position_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.10"))
    status: Mapped[str] = mapped_column(String(12), default="open")  # open | closed


class AiDecision(Base):
    """Toda salida del LLM queda auditada (fase 3)."""

    __tablename__ = "ai_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    symbol: Mapped[str] = mapped_column(String(12))
    action: Mapped[str] = mapped_column(String(12))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    model_version: Mapped[str] = mapped_column(String(64), default="")


class KillSwitchEvent(Base):
    __tablename__ = "kill_switch_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    actor: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(8))  # halt | resume
    reason: Mapped[str] = mapped_column(Text, default="")


class PortfolioSnapshot(Base):
    """Foto diaria del portafolio: la curva de equity del dashboard."""

    __tablename__ = "portfolio_snapshots"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    cash_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    positions_value_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    equity_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class Fundamental(Base):
    """Fundamentales SEC EDGAR con fecha de PUBLICACIÓN (point-in-time)."""

    __tablename__ = "fundamentals"
    __table_args__ = (
        UniqueConstraint("symbol", "metric", "period_end", "filed", name="uq_fund_row"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(12), index=True)
    metric: Mapped[str] = mapped_column(String(32))
    period_end: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    filed: Mapped[date] = mapped_column(Date)  # desde esta fecha el dato EXISTE
    form: Mapped[str] = mapped_column(String(8), default="")


class SystemFlag(Base):
    __tablename__ = "system_flags"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(String(64))
