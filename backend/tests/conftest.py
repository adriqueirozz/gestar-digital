import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registra as tabelas)
from app.database import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def ligar_chaves(conexao, _):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao