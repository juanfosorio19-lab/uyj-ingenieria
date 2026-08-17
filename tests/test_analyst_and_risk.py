import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db import make_session_factory
from app.llm.analyst import (
    RulesAnalyst,
    ThesisProposal,
    analyze,
    build_context,
    build_prompt,
)
from app.models import AiDecision, PriceBar, Thesis
from app.risk import RiskLimits, evaluate

SECRET = "sk-ant-SECRETO-QUE-NO-DEBE-FILTRARSE"


def seed_prices(engine, days=230):
    """WIN con tendencia fuerte, LOSE cayendo, SPY plano. Suficiente historia."""
    start = date(2026, 1, 5)
    with Session(engine) as s:
        for i in range(days):
            day = start + timedelta(days=i)
            if day.weekday() >= 5:
                continue
            for symbol, price in [
                ("WIN", 100 * (1.002**i)),
                ("LOSE", 100 * (0.998**i)),
                ("SPY", 100.0),
            ]:
                value = Decimal(str(round(price, 4)))
                s.add(
                    PriceBar(
                        symbol=symbol, date=day, open=value, high=value,
                        low=value, close=value, volume=1000,
                    )
                )
        s.commit()


class BadJsonClient:
    model_version = "bad-v1"

    def complete(self, system, user):
        return "esto no es json, es un desastre"


class SchemaViolatingClient:
    model_version = "cheat-v1"

    def complete(self, system, user):
        # JSON válido pero pide 50% del portafolio: debe rechazarse por esquema
        return json.dumps(
            {
                "action": "buy",
                "symbol": "WIN",
                "thesis": "Quiero apostar todo a una sola carta ahora mismo.",
                "invalidators": [{"metric": "price_vs_entry", "op": "<", "value": -0.2}],
                "target_horizon_days": 60,
                "max_position_pct": 0.50,
                "confidence": 0.9,
            }
        )


def make_proposal(**overrides) -> ThesisProposal:
    base = {
        "action": "buy",
        "symbol": "WIN",
        "thesis": "Momentum sostenido con invalidadores claros.",
        "invalidators": [{"metric": "price_vs_entry", "op": "<", "value": -0.2}],
        "target_horizon_days": 60,
        "max_position_pct": 0.05,
        "confidence": 0.6,
    }
    base.update(overrides)
    return ThesisProposal.model_validate(base)


# ---- BLOQUEANTE 1: ningún secreto llega al prompt --------------------------


def test_secrets_never_reach_the_prompt(engine, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", SECRET)
    from app.config import get_settings

    get_settings.cache_clear()  # fuerza a releer el entorno con los secretos
    try:
        seed_prices(engine)
        sf = make_session_factory(engine)
        context = build_context(sf)
        system, user = build_prompt(context)
        assert SECRET not in system
        assert SECRET not in user
        # el user es exactamente el dict allowlist: claves conocidas y nada más
        assert set(json.loads(user).keys()) == {"as_of", "candidates", "positions", "cash_usd"}
    finally:
        get_settings.cache_clear()


# ---- BLOQUEANTE 2: JSON inválido se rechaza y se audita, jamás se usa ------


def test_malformed_json_is_rejected_and_audited(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    outcome = analyze(sf, client=BadJsonClient())

    assert outcome.status == "rejected_schema"
    assert outcome.proposal is None
    with Session(engine) as s:
        decisions = s.query(AiDecision).all()
        assert len(decisions) == 1
        assert decisions[0].action == "rejected_sche"[:12] or decisions[0].action.startswith(
            "rejected"
        )
        assert s.query(Thesis).count() == 0  # nada entra al sistema


def test_schema_limits_block_oversized_positions(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    outcome = analyze(sf, client=SchemaViolatingClient())
    assert outcome.status == "rejected_schema"  # 50% > tope 10% del esquema
    with Session(engine) as s:
        assert s.query(Thesis).count() == 0


# ---- flujo feliz con el analista de reglas ---------------------------------


def test_rules_analyst_full_flow(engine):
    seed_prices(engine)
    sf = make_session_factory(engine)
    outcome = analyze(sf, client=RulesAnalyst())

    assert outcome.status == "ok"
    assert outcome.proposal.action == "buy"
    assert outcome.proposal.symbol == "WIN"  # el momentum más alto
    assert outcome.proposal.invalidators  # compra sin invalidadores no existe
    with Session(engine) as s:
        decision = s.query(AiDecision).one()
        assert len(decision.prompt_hash) == 64  # sha256 auditado
        assert decision.model_version == "rules-v1"
        thesis = s.query(Thesis).one()
        assert thesis.symbol == "WIN"
        assert thesis.invalidators[0]["metric"] == "price_vs_entry"


# ---- Risk Engine: funciones puras ------------------------------------------


def test_risk_approves_within_limits():
    verdict = evaluate(
        make_proposal(),
        cash_usd=10000,
        portfolio_value_usd=10000,
        current_positions={},
        kill_switch_enabled=True,
    )
    assert verdict.approved


def test_risk_rejects_kill_switch_and_concentration():
    verdict = evaluate(
        make_proposal(max_position_pct=0.10),
        cash_usd=10000,
        portfolio_value_usd=10000,
        current_positions={"WIN": 900.0},  # 9% existente + 10% nuevo = 19%
        kill_switch_enabled=False,
    )
    assert not verdict.approved
    assert any("kill switch" in r for r in verdict.reasons)
    assert any("concentración" in r for r in verdict.reasons)


def test_risk_rejects_when_cash_or_slots_missing():
    many = {f"P{i}": 100.0 for i in range(8)}
    verdict = evaluate(
        make_proposal(),
        cash_usd=100.0,  # pide 5% de 10k = 500 > 100 de caja
        portfolio_value_usd=10000,
        current_positions=many,
        kill_switch_enabled=True,
        limits=RiskLimits(max_positions=8),
    )
    assert not verdict.approved
    assert any("caja insuficiente" in r for r in verdict.reasons)
    assert any("máx 8" in r for r in verdict.reasons)


def test_hold_is_always_approved():
    verdict = evaluate(
        make_proposal(action="hold", invalidators=[]),
        cash_usd=0,
        portfolio_value_usd=0,
        current_positions={},
        kill_switch_enabled=False,
    )
    assert verdict.approved
