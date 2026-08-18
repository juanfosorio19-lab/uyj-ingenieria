import json

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brokers.alpaca import AlpacaAdapter
from app.brokers.base import OrderRejected
from app.brokers.paper import PaperAdapter
from app.controls import orders_enabled, set_orders_enabled
from app.db import make_session_factory
from app.llm.analyst import RulesAnalyst, analyze
from app.models import Position, Reconciliation
from app.trade import reconcile, sync_positions, trade_once
from tests.test_analyst_and_risk import seed_prices


class FakeAlpaca:
    """Servidor Alpaca simulado detrás de httpx.MockTransport."""

    def __init__(self):
        self.orders: dict[str, dict] = {}
        self.positions: list[dict] = []
        self.order_posts = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v2/account":
            return httpx.Response(200, json={"cash": "100000"})
        if path == "/v2/positions":
            return httpx.Response(200, json=self.positions)
        if path == "/v2/clock":
            return httpx.Response(200, json={"is_open": False})
        if path == "/v2/orders" and request.method == "POST":
            self.order_posts += 1
            payload = json.loads(request.content)
            cid = payload["client_order_id"]
            if cid in self.orders:
                return httpx.Response(
                    422, json={"message": "client_order_id must be unique"}
                )
            order = {
                "symbol": payload["symbol"], "side": payload["side"],
                "qty": payload["qty"], "status": "accepted",
                "filled_avg_price": None, "client_order_id": cid,
            }
            self.orders[cid] = order
            return httpx.Response(200, json=order)
        if path == "/v2/orders:by_client_order_id":
            cid = request.url.params["client_order_id"]
            if cid in self.orders:
                return httpx.Response(200, json=self.orders[cid])
            return httpx.Response(404, json={"message": "not found"})
        return httpx.Response(500, json={"message": f"ruta no simulada: {path}"})


def make_alpaca(engine, fake: FakeAlpaca) -> AlpacaAdapter:
    return AlpacaAdapter(
        make_session_factory(engine),
        api_key="k", secret_key="s",
        transport=httpx.MockTransport(fake.handler),
    )


def test_alpaca_reads_account_positions_clock(engine):
    fake = FakeAlpaca()
    fake.positions = [{"symbol": "AAPL", "qty": "5", "avg_entry_price": "200"}]
    adapter = make_alpaca(engine, fake)
    assert float(adapter.get_cash()) == 100000
    assert adapter.get_positions()[0].symbol == "AAPL"
    assert adapter.is_market_open() is False


def test_alpaca_idempotency_via_422(engine):
    from decimal import Decimal

    fake = FakeAlpaca()
    adapter = make_alpaca(engine, fake)
    first = adapter.place_order("NVDA", "buy", Decimal(2), "clave-1")
    second = adapter.place_order("NVDA", "buy", Decimal(2), "clave-1")
    assert first.duplicate is False
    assert second.duplicate is True
    assert len(fake.orders) == 1  # el broker solo vio UNA orden real


def test_alpaca_respects_kill_switch_before_network(engine):
    from decimal import Decimal

    import pytest

    fake = FakeAlpaca()
    adapter = make_alpaca(engine, fake)
    sf = make_session_factory(engine)
    set_orders_enabled(sf, False, actor="test")
    with pytest.raises(OrderRejected, match="Kill switch"):
        adapter.place_order("NVDA", "buy", Decimal(1), "clave-2")
    assert fake.order_posts == 0  # jamás llegó a la red


def test_reconcile_unexplained_divergence_halts_system(engine):
    fake = FakeAlpaca()
    fake.positions = [{"symbol": "AAPL", "qty": "10", "avg_entry_price": "200"}]
    adapter = make_alpaca(engine, fake)
    sf = make_session_factory(engine)
    # local dice otra cosa y NO hay ninguna orden nuestra que lo explique
    with Session(engine) as s:
        s.add(Position(symbol="AAPL", qty=3, avg_price_usd=200))
        s.commit()

    assert reconcile(sf, adapter) is False
    assert orders_enabled(sf) is False  # HALT automático
    with Session(engine) as s:
        rec = s.scalars(select(Reconciliation)).one()
        assert rec.status == "divergent"


def test_reconcile_heals_fill_lag(engine):
    """El caso real del 17-08: orden puesta, fill posterior al sync => sanar solo."""
    from decimal import Decimal

    fake = FakeAlpaca()
    adapter = make_alpaca(engine, fake)
    sf = make_session_factory(engine)

    # el agente compró (queda orden local "accepted"); el sync corrió ANTES del fill
    adapter.place_order("AMD", "buy", Decimal("15.6724"), "trade-2026-08-17-AMD-buy")
    sync_positions(sf, adapter)  # broker aún sin posición => espejo local vacío

    # ...y después Alpaca llena la orden
    fake.positions = [{"symbol": "AMD", "qty": "15.6724", "avg_entry_price": "170"}]
    fake.orders["trade-2026-08-17-AMD-buy"]["status"] = "filled"

    assert reconcile(sf, adapter) is True  # divergencia EXPLICADA: no hay HALT
    assert orders_enabled(sf) is True
    with Session(engine) as s:
        recs = s.scalars(select(Reconciliation).order_by(Reconciliation.id)).all()
        assert recs[-1].status == "healed"
        local = s.scalars(select(Position)).one()
        assert local.symbol == "AMD"  # espejo re-sincronizado desde el broker
        from app.models import Order

        order = s.scalars(select(Order)).one()
        assert order.status == "filled"  # estado refrescado desde Alpaca


def test_sync_positions_mirrors_broker(engine):
    fake = FakeAlpaca()
    fake.positions = [{"symbol": "MSFT", "qty": "7", "avg_entry_price": "400"}]
    adapter = make_alpaca(engine, fake)
    sf = make_session_factory(engine)
    with Session(engine) as s:
        s.add(Position(symbol="VIEJA", qty=1, avg_price_usd=1))
        s.commit()
    sync_positions(sf, adapter)
    with Session(engine) as s:
        rows = s.scalars(select(Position)).all()
        assert [r.symbol for r in rows] == ["MSFT"]


def test_trade_once_executes_and_is_idempotent(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    adapter = PaperAdapter(sf)

    first = trade_once(sf, adapter, client=RulesAnalyst())
    assert "EJECUTADA" in first
    assert "WIN" in first
    with Session(engine) as s:
        position = s.scalars(select(Position)).one()
        assert position.symbol == "WIN"
        qty_after_first = float(position.qty)

    second = trade_once(sf, adapter, client=RulesAnalyst())
    assert "idempotente" in second  # mismo día => misma clave => no duplica
    with Session(engine) as s:
        assert float(s.scalars(select(Position)).one().qty) == qty_after_first


def test_analyst_tolerates_markdown_fences(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)

    class FencedClient:
        model_version = "fenced-v1"

        def complete(self, system, user):
            inner = RulesAnalyst().complete(system, user)
            return f"```json\n{inner}\n```"

    outcome = analyze(sf, client=FencedClient())
    assert outcome.status == "ok"
    assert outcome.proposal.action == "buy"


def test_invalidator_accepts_string_only_with_equality():
    import pytest
    from pydantic import ValidationError

    from app.llm.analyst import Invalidator

    ok = Invalidator(metric="guidance_revision", op="==", value="down")
    assert ok.value == "down"
    with pytest.raises(ValidationError):
        Invalidator(metric="guidance_revision", op="<", value="down")
