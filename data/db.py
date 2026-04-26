from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from data.models import Base


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    return SessionLocal()


def test_db_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
