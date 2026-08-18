import os
from decimal import Decimal

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Account, Base, SystemFlag

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite:///./"):
            os.makedirs(os.path.dirname(url.removeprefix("sqlite:///")) or ".", exist_ok=True)
        _engine = create_engine(url)
    return _engine


def init_db(engine: Engine, starting_cash: Decimal | None = None) -> None:
    """Crea el esquema y siembra caja inicial + flag de órdenes. Idempotente."""
    Base.metadata.create_all(engine)
    cash = starting_cash if starting_cash is not None else Decimal(get_settings().starting_cash_usd)
    with Session(engine) as s:
        if s.get(Account, 1) is None:
            s.add(Account(id=1, cash_usd=cash))
        if s.get(SystemFlag, "orders_enabled") is None:
            s.add(SystemFlag(key="orders_enabled", value="true"))
        s.commit()


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
