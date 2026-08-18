"""Elegir broker es una línea de configuración: BROKER=paper|alpaca."""

from sqlalchemy.orm import Session, sessionmaker

from app.brokers.alpaca import AlpacaAdapter
from app.brokers.paper import PaperAdapter
from app.config import get_settings


def make_adapter(session_factory: sessionmaker[Session]):
    settings = get_settings()
    if settings.broker == "alpaca":
        if not (settings.alpaca_api_key and settings.alpaca_secret_key):
            raise RuntimeError(
                "BROKER=alpaca pero faltan ALPACA_API_KEY/ALPACA_SECRET_KEY en el .env"
            )
        return AlpacaAdapter(
            session_factory,
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            base_url=settings.alpaca_base_url,
        )
    return PaperAdapter(session_factory)
