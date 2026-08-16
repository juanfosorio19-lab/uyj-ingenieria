import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from app.brokers.base import OrderRejected
from app.brokers.paper import PaperAdapter
from app.controls import orders_enabled
from app.db import get_engine, init_db, make_session_factory


class OrderIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    side: Literal["buy", "sell"]
    qty: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    client_order_id: str | None = None


def create_app(engine: Engine | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        eng = engine or get_engine()
        init_db(eng)
        app.state.session_factory = make_session_factory(eng)
        app.state.adapter = PaperAdapter(app.state.session_factory)
        yield

    app = FastAPI(title="Trading Agent", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/status")
    def status(request: Request) -> dict:
        adapter = request.app.state.adapter
        return {
            "broker": adapter.name,
            "cash_usd": float(adapter.get_cash()),
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_price_usd": float(p.avg_price_usd),
                }
                for p in adapter.get_positions()
            ],
            "orders_enabled": orders_enabled(request.app.state.session_factory),
            "market_open": adapter.is_market_open(),
        }

    @app.post("/orders", status_code=201)
    def place_order(order: OrderIn, request: Request) -> dict:
        adapter = request.app.state.adapter
        key = order.client_order_id or str(uuid.uuid4())
        try:
            result = adapter.place_order(
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                idempotency_key=key,
                price=order.price,
            )
        except OrderRejected as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "client_order_id": result.client_order_id,
            "symbol": result.symbol,
            "side": result.side,
            "qty": float(result.qty),
            "fill_price_usd": float(result.fill_price_usd),
            "status": result.status,
            "duplicate": result.duplicate,
        }

    return app


app = create_app()
