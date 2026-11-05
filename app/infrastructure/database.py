import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

# Neon suspende el cómputo y cierra conexiones ociosas: pre_ping descarta las muertas.
engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base de los modelos ORM. Alembic lee su metadata."""


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_database_reachable() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        logger.exception("No se pudo conectar a la base de datos")
        return False
