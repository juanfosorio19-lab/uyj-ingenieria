"""Analista: propone una tesis falsable. NUNCA ejecuta.

Reglas duras de seguridad (sección 6 del plan original):
1. Allowlist, no denylist: el prompt se construye SOLO desde un dict
   explícito (precios, scores, posiciones, caja). Nunca `os.environ`,
   nunca `settings` completos. Si un dato no está en el dict, no existe
   para el modelo.
2. El LLM no tiene herramientas: devuelve JSON y punto.
3. Validación Pydantic: JSON que no calza → rechazado y registrado,
   jamás ejecutado.
4. Auditoría: toda salida queda en `ai_decisions` con prompt_hash y
   model_version.

Sin ANTHROPIC_API_KEY configurada, `RulesAnalyst` genera la propuesta con
las mismas reglas de momentum del backtest: el circuito completo funciona
sin IA, y la IA se enchufa con una variable de entorno.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.orm import Session, sessionmaker

from app.backtest import load_close_matrix
from app.brokers.paper import PaperAdapter
from app.config import get_settings
from app.models import AiDecision, Thesis
from app.scoring import LOOKBACK, SKIP, momentum_scores
from app.universe import BENCHMARK

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- contexto --


@dataclass
class Candidate:
    symbol: str
    momentum: float
    last_close: float


@dataclass
class AllowedContext:
    """TODO lo que el modelo puede ver. Nada más entra al prompt."""

    as_of: str
    candidates: list[Candidate]
    positions: list[dict]
    cash_usd: float

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "candidates": [
                {"symbol": c.symbol, "momentum_6m1m": round(c.momentum, 4),
                 "last_close_usd": round(c.last_close, 2)}
                for c in self.candidates
            ],
            "positions": self.positions,
            "cash_usd": round(self.cash_usd, 2),
        }


def build_context(session_factory: sessionmaker[Session]) -> AllowedContext | None:
    closes = load_close_matrix(session_factory)
    if closes.empty or len(closes) < LOOKBACK + SKIP + 2:
        return None
    candidates_frame = closes[[c for c in closes.columns if c != BENCHMARK]]
    scores = momentum_scores(candidates_frame, at=len(closes) - 1)
    if scores.empty:
        return None
    top = scores.nlargest(10)
    last_row = closes.iloc[-1]
    adapter = PaperAdapter(session_factory)
    return AllowedContext(
        as_of=str(closes.index[-1]),
        candidates=[
            Candidate(symbol=str(sym), momentum=float(val), last_close=float(last_row[sym]))
            for sym, val in top.items()
        ],
        positions=[
            {"symbol": p.symbol, "qty": float(p.qty), "avg_price_usd": float(p.avg_price_usd)}
            for p in adapter.get_positions()
        ],
        cash_usd=float(adapter.get_cash()),
    )


# ------------------------------------------------------------------ schema --


class Invalidator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=2, max_length=40)
    op: Literal["<", ">", "<=", ">=", "=="]
    value: float


class ThesisProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["buy", "hold"]
    symbol: str = Field(min_length=1, max_length=12)
    thesis: str = Field(min_length=10, max_length=1000)
    invalidators: list[Invalidator] = Field(default_factory=list, max_length=6)
    target_horizon_days: int = Field(ge=5, le=365)
    max_position_pct: float = Field(gt=0, le=0.10)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _buy_requires_invalidators(self):
        if self.action == "buy" and not self.invalidators:
            raise ValueError("una compra exige invalidadores medibles")
        return self


SYSTEM_PROMPT = """Eres el analista de un agente de inversión. Recibes un JSON \
con candidatos (momentum 6m-1m), posiciones actuales y caja. Propones a lo más \
UNA acción para mañana: comprar un candidato o mantener.

Respondes SOLO con un JSON válido con esta forma exacta, sin texto adicional:
{"action": "buy"|"hold", "symbol": str, "thesis": str (10-1000 chars, en español),
 "invalidators": [{"metric": str, "op": "<"|">"|"<="|">="|"==", "value": number}],
 "target_horizon_days": int (5-365), "max_position_pct": number (0-0.10),
 "confidence": number (0-1)}

Reglas: la tesis debe ser falsable y los invalidadores medibles (p.ej. \
price_vs_entry < -0.20). Si compras, incluye 2-4 invalidadores. Horizonte \
mínimo 5 días (baja rotación: los impuestos castigan realizar ganancias). \
Un motor de riesgo determinista valida tu propuesta y puede rechazarla; \
tú no ejecutas nada."""


def build_prompt(context: AllowedContext) -> tuple[str, str]:
    """(system, user). El user es EXACTAMENTE el dict allowlist, nada más."""
    return SYSTEM_PROMPT, json.dumps(context.to_dict(), ensure_ascii=False)


# ----------------------------------------------------------------- clientes --


class AnalystClient(Protocol):
    model_version: str

    def complete(self, system: str, user: str) -> str: ...


class RulesAnalyst:
    """Fallback determinista sin IA: mismas reglas de momentum del backtest."""

    model_version = "rules-v1"

    def complete(self, system: str, user: str) -> str:
        context = json.loads(user)
        candidates = context.get("candidates") or []
        best = candidates[0] if candidates else None
        if best is None or best["momentum_6m1m"] <= 0:
            proposal = {
                "action": "hold",
                "symbol": best["symbol"] if best else "SPY",
                "thesis": "Ningún candidato con momentum positivo; mantener y esperar.",
                "invalidators": [],
                "target_horizon_days": 30,
                "max_position_pct": 0.01,
                "confidence": 0.5,
            }
        else:
            proposal = {
                "action": "buy",
                "symbol": best["symbol"],
                "thesis": (
                    f"Momentum 6m-1m de {best['momentum_6m1m']:+.1%} lidera el universo; "
                    "la tendencia se mantiene mientras no se activen los invalidadores."
                ),
                "invalidators": [
                    {"metric": "price_vs_entry", "op": "<", "value": -0.20},
                    {"metric": "momentum_6m1m", "op": "<", "value": 0},
                ],
                "target_horizon_days": 60,
                "max_position_pct": 0.05,
                "confidence": 0.55,
            }
        return json.dumps(proposal, ensure_ascii=False)


class AnthropicAnalyst:
    """Analista con Claude. Solo ve el dict allowlist; sin herramientas."""

    def __init__(self, model: str, api_key: str):
        from anthropic import Anthropic  # import perezoso

        self._client = Anthropic(api_key=api_key)
        self.model_version = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self.model_version,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in response.content if block.type == "text"]
        return "".join(parts).strip()


def make_client() -> AnalystClient:
    settings = get_settings()
    if settings.anthropic_api_key:
        return AnthropicAnalyst(settings.llm_model, settings.anthropic_api_key)
    return RulesAnalyst()


# ----------------------------------------------------------------- análisis --


@dataclass
class AnalysisOutcome:
    status: str  # "ok" | "rejected_schema" | "no_data" | "error"
    proposal: ThesisProposal | None = None
    raw: str = ""


def analyze(
    session_factory: sessionmaker[Session], client: AnalystClient | None = None
) -> AnalysisOutcome:
    context = build_context(session_factory)
    if context is None:
        return AnalysisOutcome(status="no_data")

    client = client or make_client()
    system, user = build_prompt(context)
    prompt_hash = hashlib.sha256((system + user).encode()).hexdigest()

    try:
        raw = client.complete(system, user)
    except Exception:
        log.exception("El analista falló")
        _audit(session_factory, "?", "error", {"error": "client"}, prompt_hash, client)
        return AnalysisOutcome(status="error")

    try:
        proposal = ThesisProposal.model_validate_json(raw)
    except ValidationError as exc:
        log.warning("Propuesta rechazada por esquema: %s", exc.error_count())
        _audit(
            session_factory,
            "?",
            "rejected_schema",
            {"raw": raw[:4000], "errors": exc.error_count()},
            prompt_hash,
            client,
        )
        return AnalysisOutcome(status="rejected_schema", raw=raw)

    _audit(
        session_factory,
        proposal.symbol,
        proposal.action,
        {"proposal": proposal.model_dump()},
        prompt_hash,
        client,
    )
    if proposal.action == "buy":
        with session_factory() as s:
            s.add(
                Thesis(
                    symbol=proposal.symbol,
                    thesis=proposal.thesis,
                    invalidators=[i.model_dump() for i in proposal.invalidators],
                    target_horizon_days=proposal.target_horizon_days,
                    max_position_pct=proposal.max_position_pct,
                    created_at=datetime.now(UTC),
                )
            )
            s.commit()
    return AnalysisOutcome(status="ok", proposal=proposal, raw=raw)


def _audit(session_factory, symbol, action, payload, prompt_hash, client) -> None:
    with session_factory() as s:
        s.add(
            AiDecision(
                symbol=symbol[:12],
                action=action[:12],
                payload=payload,
                prompt_hash=prompt_hash,
                model_version=getattr(client, "model_version", "?"),
            )
        )
        s.commit()
