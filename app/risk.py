"""Risk Engine determinista. La IA propone; estas reglas deciden.

Funciones puras: entran números, sale un veredicto con razones. El LLM no
participa aquí — jamás. Las 5 reglas de salida del plan (stop duro,
invalidadores, horizonte, concentración, mantener) se implementan en la
fase 4 junto con la ejecución; aquí viven las reglas de ENTRADA.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from app.brokers.paper import PaperAdapter
from app.controls import orders_enabled
from app.llm.analyst import ThesisProposal


@dataclass
class RiskLimits:
    max_position_pct: float = 0.10  # ninguna posición supera el 10% del portafolio
    max_positions: int = 8
    min_confidence: float = 0.3


@dataclass
class RiskVerdict:
    approved: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.approved:
            return "APROBADA ✅ (dentro de límites)"
        return "RECHAZADA 🛑: " + "; ".join(self.reasons)


def evaluate(
    proposal: ThesisProposal,
    *,
    cash_usd: float,
    portfolio_value_usd: float,
    current_positions: dict[str, float],  # symbol -> valor USD
    kill_switch_enabled: bool,
    limits: RiskLimits | None = None,
) -> RiskVerdict:
    limits = limits or RiskLimits()
    if proposal.action == "hold":
        return RiskVerdict(approved=True)

    reasons: list[str] = []
    if not kill_switch_enabled:
        reasons.append("kill switch activo")
    if proposal.max_position_pct > limits.max_position_pct:
        reasons.append(
            f"pide {proposal.max_position_pct:.0%} y el límite es {limits.max_position_pct:.0%}"
        )
    if proposal.confidence < limits.min_confidence:
        reasons.append(f"confianza {proposal.confidence:.2f} bajo el mínimo")

    order_value = proposal.max_position_pct * portfolio_value_usd
    if order_value > cash_usd:
        reasons.append(f"caja insuficiente ({order_value:.0f} > {cash_usd:.0f})")

    existing_value = current_positions.get(proposal.symbol, 0.0)
    if portfolio_value_usd > 0:
        resulting_pct = (existing_value + order_value) / portfolio_value_usd
        if resulting_pct > limits.max_position_pct + 1e-9:
            reasons.append(
                f"concentración resultante {resulting_pct:.0%} supera "
                f"{limits.max_position_pct:.0%} en {proposal.symbol}"
            )
    is_new = proposal.symbol not in current_positions
    if is_new and len(current_positions) >= limits.max_positions:
        reasons.append(f"ya hay {len(current_positions)} posiciones (máx {limits.max_positions})")

    return RiskVerdict(approved=not reasons, reasons=reasons)


def evaluate_from_db(
    session_factory: sessionmaker[Session], proposal: ThesisProposal
) -> RiskVerdict:
    """Arma los insumos desde el estado real y llama a la función pura."""
    adapter = PaperAdapter(session_factory)
    cash = float(adapter.get_cash())
    positions = {
        p.symbol: float(Decimal(p.qty) * Decimal(p.avg_price_usd))
        for p in adapter.get_positions()
    }
    portfolio_value = cash + sum(positions.values())
    return evaluate(
        proposal,
        cash_usd=cash,
        portfolio_value_usd=portfolio_value,
        current_positions=positions,
        kill_switch_enabled=orders_enabled(session_factory),
    )
