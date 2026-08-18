from fastapi.testclient import TestClient

from app.main import create_app


def test_health_status_and_order_flow(engine):
    app = create_app(engine=engine)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        response = client.post(
            "/orders", json={"symbol": "aapl", "side": "buy", "qty": 5, "price": 100}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert body["status"] == "filled"
        assert body["duplicate"] is False

        status = client.get("/status").json()
        assert status["cash_usd"] == 9500.0
        assert status["orders_enabled"] is True
        assert status["positions"] == [
            {"symbol": "AAPL", "qty": 5.0, "avg_price_usd": 100.0}
        ]


def test_order_rejection_returns_409(engine):
    app = create_app(engine=engine)
    with TestClient(app) as client:
        response = client.post(
            "/orders", json={"symbol": "AAPL", "side": "sell", "qty": 1, "price": 100}
        )
        assert response.status_code == 409
        assert "Posición insuficiente" in response.json()["detail"]


def test_order_idempotency_via_api(engine):
    app = create_app(engine=engine)
    with TestClient(app) as client:
        payload = {
            "symbol": "NVDA",
            "side": "buy",
            "qty": 2,
            "price": 120,
            "client_order_id": "n8n-retry-1",
        }
        first = client.post("/orders", json=payload).json()
        second = client.post("/orders", json=payload).json()
        assert first["duplicate"] is False
        assert second["duplicate"] is True
        status = client.get("/status").json()
        assert status["positions"][0]["qty"] == 2.0
