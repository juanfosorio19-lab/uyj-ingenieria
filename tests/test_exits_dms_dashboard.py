from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brokers.base import PositionInfo
from app.brokers.paper import PaperAdapter
from app.controls import orders_enabled, record_heartbeat
from app.db import make_session_factory
from app.exits import check_and_execute_exits, evaluate_exit
from app.llm.analyst import RulesAnalyst
from app.main import create_app
from app.models import PortfolioSnapshot, PriceBar, SystemFlag, Thesis
from app.trade import snapshot_portfolio, trade_once
from tests.test_analyst_and_risk import seed_prices


def pos(symbol="WIN", qty="10", entry="100") -> PositionInfo:
    return PositionInfo(symbol=symbol, qty=Decimal(qty), avg_price_usd=Decimal(entry))


def thesis(days_ago=10, horizon=60, invalidators=None) -> Thesis:
    return Thesis(
        symbol="WIN",
        thesis="tesis de prueba",
        invalidators=invalidators or [],
        target_horizon_days=horizon,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
        status="open",
    )


TODAY = date(2026, 8, 17)
PV = Decimal(10000)


def test_hard_stop_beats_everything():
    action = evaluate_exit(
        pos(), thesis(), current_price=Decimal(79), momentum=1.0,
        today=TODAY, portfolio_value=PV,
    )
    assert action.rule == "stop_duro"
    assert action.sells_all


def test_invalidator_price_vs_entry():
    inv = [{"metric": "price_vs_entry", "op": "<", "value": -0.1}]
    action = evaluate_exit(
        pos(), thesis(invalidators=inv), current_price=Decimal(88), momentum=None,
        today=TODAY, portfolio_value=PV,
    )
    assert action.rule == "invalidador"
    assert "price_vs_entry" in action.reason


def test_invalidator_days_held_and_momentum():
    inv = [{"metric": "days_held", "op": ">", "value": 90}]
    action = evaluate_exit(
        pos(), thesis(days_ago=120, horizon=365, invalidators=inv),
        current_price=Decimal(105), momentum=None, today=TODAY, portfolio_value=PV,
    )
    assert action.rule == "invalidador"

    inv = [{"metric": "momentum_6m1m", "op": "<", "value": 0.3}]
    action = evaluate_exit(
        pos(), thesis(invalidators=inv), current_price=Decimal(105), momentum=0.1,
        today=TODAY, portfolio_value=PV,
    )
    assert action.rule == "invalidador"


def test_unknown_invalidator_metric_is_skipped():
    inv = [{"metric": "guidance_revision", "op": "==", "value": "down"}]
    action = evaluate_exit(
        pos(qty="5"), thesis(invalidators=inv), current_price=Decimal(105), momentum=None,
        today=TODAY, portfolio_value=PV,  # 525/10000: lejos del límite de concentración
    )
    assert action is None  # no evaluable mecánicamente => mantener


def test_horizon_expiry_sells():
    action = evaluate_exit(
        pos(), thesis(days_ago=61, horizon=60), current_price=Decimal(105),
        momentum=None, today=TODAY, portfolio_value=PV,
    )
    assert action.rule == "horizonte"


def test_concentration_trims_to_limit():
    action = evaluate_exit(
        pos(qty="20", entry="100"), None, current_price=Decimal(100),
        momentum=None, today=TODAY, portfolio_value=PV,  # 2000/10000 = 20%
    )
    assert action.rule == "concentracion"
    assert not action.sells_all
    assert action.qty == Decimal(10)  # recorta 1000/100 para volver al 10%


def test_executor_sells_on_stop_and_closes_thesis(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    adapter = PaperAdapter(sf)
    trade_once(sf, adapter, client=RulesAnalyst())  # compra WIN a último cierre

    # desplome: nuevo cierre 30% abajo del precio de entrada
    with Session(engine) as s:
        last = s.scalar(
            select(PriceBar).where(PriceBar.symbol == "WIN").order_by(PriceBar.date.desc())
        )
        crash = (Decimal(last.close) * Decimal("0.7")).quantize(Decimal("0.0001"))
        s.add(PriceBar(symbol="WIN", date=last.date + timedelta(days=1), open=crash,
                       high=crash, low=crash, close=crash, volume=1000))
        s.commit()

    messages = check_and_execute_exits(sf, adapter)
    assert len(messages) == 1
    assert "stop_duro" in messages[0]
    assert adapter.get_positions() == []  # vendida completa
    with Session(engine) as s:
        assert s.scalars(select(Thesis).where(Thesis.status == "open")).all() == []

    assert check_and_execute_exits(sf, adapter) == []  # nada más que hacer


def test_dead_man_switch_blocks_new_buys(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    adapter = PaperAdapter(sf)

    # monitor armado pero con latido viejo (2 horas)
    stale = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    with Session(engine) as s:
        s.add(SystemFlag(key="heartbeat_monitor", value=stale))
        s.commit()

    msg = trade_once(sf, adapter, client=RulesAnalyst())
    assert "Dead man's switch" in msg
    assert adapter.get_positions() == []  # no compró
    assert orders_enabled(sf) is False  # y apagó el flag global


def test_fresh_heartbeat_allows_trading(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    record_heartbeat(sf, key="monitor")
    msg = trade_once(sf, PaperAdapter(sf), client=RulesAnalyst())
    assert "EJECUTADA" in msg


def test_snapshot_and_dashboard(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    adapter = PaperAdapter(sf)
    trade_once(sf, adapter, client=RulesAnalyst())
    snapshot_portfolio(sf, adapter)

    with Session(engine) as s:
        snap = s.scalars(select(PortfolioSnapshot)).one()
        assert float(snap.equity_usd) > 0

    app = create_app(engine=engine)
    with TestClient(app) as client:
        page = client.get("/").text
        assert "Agente de trading" in page
        assert "WIN" in page  # la posición aparece
        assert "Dead man" in page
        assert "Reconciliaciones" in page
