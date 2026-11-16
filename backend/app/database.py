from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

eh_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if eh_sqlite else {})

if eh_sqlite:
    @event.listens_for(engine, "connect")
    def ativar_chaves_estrangeiras(conexao, _):
        # SQLite ignora FOREIGN KEY se isso não for ligado
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()