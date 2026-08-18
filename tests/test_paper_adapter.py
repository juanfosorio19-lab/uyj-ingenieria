from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.brokers.base import OrderRejected
from app.brokers.paper import PaperAdapter
from app.controls import set_orders_enabled
from app.db import make_session_factory
from app.models import Order, TaxLot, TaxLotClosing


def test_buy_creates_position_and_reduces_cash(adapter):
    adapter.place_order("aapl", "buy", Decimal(10), "k1", price=Decimal(100))
    positions = adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].qty == Decimal(10)
    assert adapter.get_cash() == Decimal(9000)


def test_sell_closes_lots_fifo(adapter, engine):
    adapter.place_order("NVDA", "buy", Decimal(10), "k1", price=Decimal(100))
    adapter.place_order("NVDA", "buy", Decimal(10), "k2", price=Decimal(120))
    adapter.place_order("NVDA", "sell", Decimal(15), "k3", price=Decimal(130))

    assert adapter.get_positions()[0].qty == Decimal(5)

    with Session(engine) as s:
        closings = s.scalars(select(TaxLotClosing).order_by(TaxLotClosing.id)).all()
        assert len(closings) == 2
        # FIFO: primero el lote de $100 completo, luego 5 del lote de $120
        assert Decimal(closings[0].qty) == Decimal(10)
        assert Decimal(closings[0].realized_gain_usd) == Decimal(300)  # (130-100)*10
        assert Decimal(closings[1].qty) == Decimal(5)
        assert Decimal(closings[1].realized_gain_usd) == Decimal(50)  # (130-120)*5
        open_lots = s.scalars(select(TaxLot).where(TaxLot.remaining_qty > 0)).all()
        assert len(open_lots) == 1
        assert Decimal(open_lots[0].remaining_qty) == Decimal(5)


def test_idempotency_same_key_executes_once(adapter, engine):
    first = adapter.place_order("AAPL", "buy", Decimal(5), "same-key", price=Decimal(100))
    second = adapter.place_order("AAPL", "buy", Decimal(5), "same-key", price=Decimal(100))

    assert first.duplicate is False
    assert second.duplicate is True
    assert adapter.get_positions()[0].qty == Decimal(5)  # no compró dos veces
    assert adapter.get_cash() == Decimal(9500)
    with Session(engine) as s:
        assert len(s.scalars(select(Order)).all()) == 1


def test_insufficient_cash_rejected(adapter):
    with pytest.raises(OrderRejected, match="Caja insuficiente"):
        adapter.place_order("AAPL", "buy", Decimal(1000), "k1", price=Decimal(100))
    assert adapter.get_positions() == []
    assert adapter.get_cash() == Decimal(10000)


def test_sell_without_position_rejected(adapter):
    with pytest.raises(OrderRejected, match="Posición insuficiente"):
        adapter.place_order("AAPL", "sell", Decimal(1), "k1", price=Decimal(100))


def test_kill_switch_blocks_orders(adapter, engine):
    sf = make_session_factory(engine)
    set_orders_enabled(sf, False, actor="test", reason="prueba")
    with pytest.raises(OrderRejected, match="Kill switch"):
        adapter.place_order("AAPL", "buy", Decimal(1), "k1", price=Decimal(100))
    set_orders_enabled(sf, True, actor="test")
    result = adapter.place_order("AAPL", "buy", Decimal(1), "k2", price=Decimal(100))
    assert result.status == "filled"


def test_positions_survive_restart(adapter, db_path):
    """Criterio de salida de la fase 0: el estado sobrevive un reinicio."""
    adapter.place_order("MSFT", "buy", Decimal(3), "k1", price=Decimal(400))

    # "Reinicio": engine y adapter nuevos sobre el mismo archivo de datos
    fresh_engine = create_engine(f"sqlite:///{db_path}")
    fresh_adapter = PaperAdapter(make_session_factory(fresh_engine))

    positions = fresh_adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "MSFT"
    assert positions[0].qty == Decimal(3)
    assert fresh_adapter.get_cash() == Decimal(8800)
