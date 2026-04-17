"""
dependencies.py — Shared FastAPI dependencies.
"""

from src.database.session import get_session


def get_db():
    """Yield a DB session, close after request."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
