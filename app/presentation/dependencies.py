"""Único punto donde la presentación se conecta con la infraestructura."""

from app.infrastructure.database import get_session, is_database_reachable

__all__ = ["get_session", "is_database_reachable"]
