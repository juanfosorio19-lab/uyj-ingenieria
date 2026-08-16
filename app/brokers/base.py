"""Contrato único de broker.

La decisión de arquitectura más importante del proyecto: todo el sistema habla
con esta interfaz. Cambiar de broker (paper → Racional manual → IBKR/Alpaca
live) es cambiar la implementación en una línea de configuración.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass
class PositionInfo:
    symbol: str
    qty: Decimal
    avg_price_usd: Decimal


@dataclass
class OrderResult:
    client_order_id: str
    symbol: str
    side: str
    qty: Decimal
    fill_price_usd: Decimal
    status: str
    duplicate: bool = False  # True si la orden ya existía (reintento idempotente)


class OrderRejected(Exception):
    """La orden no pasó las validaciones (caja, posición, kill switch)."""


class BrokerAdapter(Protocol):
    name: str

    def get_cash(self) -> Decimal: ...

    def get_positions(self) -> list[PositionInfo]: ...

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: Decimal,
        idempotency_key: str,
        price: Decimal | None = None,
    ) -> OrderResult: ...

    def get_order_status(self, client_order_id: str) -> str | None: ...

    def is_market_open(self) -> bool: ...
