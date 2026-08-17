"""Broker Alpaca (paper) vía REST, sin SDK pesado.

Mismo contrato que PaperAdapter. Idempotencia real de mercado: Alpaca
rechaza `client_order_id` repetidos (422) y nosotros devolvemos la orden
existente en vez de duplicar. El kill switch local se respeta ANTES de
tocar la red.
"""

import logging
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.brokers.base import OrderRejected, OrderResult, PositionInfo
from app.models import Order, SystemFlag

log = logging.getLogger(__name__)

PAPER_URL = "https://paper-api.alpaca.markets"


class AlpacaAdapter:
    name = "alpaca"

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        api_key: str,
        secret_key: str,
        base_url: str = PAPER_URL,
        transport: httpx.BaseTransport | None = None,
    ):
        self._sf = session_factory
        self._http = httpx.Client(
            base_url=base_url,
            headers={"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": secret_key},
            timeout=30,
            transport=transport,
        )

    # -- lecturas -----------------------------------------------------------

    def get_cash(self) -> Decimal:
        response = self._http.get("/v2/account")
        response.raise_for_status()
        return Decimal(response.json()["cash"])

    def get_positions(self) -> list[PositionInfo]:
        response = self._http.get("/v2/positions")
        response.raise_for_status()
        return [
            PositionInfo(
                symbol=p["symbol"],
                qty=Decimal(p["qty"]),
                avg_price_usd=Decimal(p["avg_entry_price"]),
            )
            for p in response.json()
        ]

    def is_market_open(self) -> bool:
        response = self._http.get("/v2/clock")
        response.raise_for_status()
        return bool(response.json()["is_open"])

    def get_order_status(self, client_order_id: str) -> str | None:
        data = self._get_by_client_id(client_order_id)
        return data["status"] if data else None

    def _get_by_client_id(self, client_order_id: str) -> dict | None:
        response = self._http.get(
            "/v2/orders:by_client_order_id", params={"client_order_id": client_order_id}
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    # -- escritura ----------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: Decimal,
        idempotency_key: str,
        price: Decimal | None = None,  # informativo: Alpaca ejecuta a mercado
    ) -> OrderResult:
        symbol = symbol.upper().strip()
        side = side.lower().strip()
        if side not in ("buy", "sell"):
            raise OrderRejected(f"Side inválido: {side!r}")
        if Decimal(qty) <= 0:
            raise OrderRejected("La cantidad debe ser positiva")

        # El kill switch local manda, ANTES de cualquier llamada de red.
        with self._sf() as s:
            flag = s.get(SystemFlag, "orders_enabled")
            if flag is not None and flag.value != "true":
                raise OrderRejected("Kill switch activo: órdenes deshabilitadas")

        response = self._http.post(
            "/v2/orders",
            json={
                "symbol": symbol,
                "qty": str(qty),
                "side": side,
                "type": "market",
                "time_in_force": "day",
                "client_order_id": idempotency_key,
            },
        )
        if response.status_code == 422 and "client_order_id" in response.text:
            existing = self._get_by_client_id(idempotency_key)
            if existing:
                return OrderResult(
                    client_order_id=idempotency_key,
                    symbol=existing["symbol"],
                    side=existing["side"],
                    qty=Decimal(existing["qty"]),
                    fill_price_usd=Decimal(existing.get("filled_avg_price") or 0),
                    status=existing["status"],
                    duplicate=True,
                )
        if response.status_code >= 400:
            raise OrderRejected(f"Alpaca rechazó la orden: {response.text[:300]}")

        data = response.json()
        fill_price = Decimal(data.get("filled_avg_price") or 0)
        self._record_order(idempotency_key, symbol, side, Decimal(qty), fill_price, data["status"])
        return OrderResult(
            client_order_id=idempotency_key,
            symbol=symbol,
            side=side,
            qty=Decimal(qty),
            fill_price_usd=fill_price,
            status=data["status"],
        )

    def _record_order(self, key, symbol, side, qty, price, status) -> None:
        with self._sf() as s:
            exists = s.scalar(select(Order).where(Order.client_order_id == key))
            if exists is None:
                s.add(
                    Order(
                        client_order_id=key,
                        symbol=symbol,
                        side=side,
                        qty=qty,
                        price_usd=price,
                        status=status[:16],
                    )
                )
                s.commit()
