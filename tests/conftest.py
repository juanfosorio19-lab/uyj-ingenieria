from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from app.brokers.paper import PaperAdapter
from app.db import init_db, make_session_factory


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "agent.db"


@pytest.fixture
def engine(db_path):
    eng = create_engine(f"sqlite:///{db_path}")
    init_db(eng, starting_cash=Decimal(10000))
    return eng


@pytest.fixture
def adapter(engine):
    return PaperAdapter(make_session_factory(engine))
