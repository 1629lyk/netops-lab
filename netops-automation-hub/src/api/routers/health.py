"""
health.py — GET /health
Returns API, database, and Redis status.
"""

import os
import redis
from fastapi import APIRouter
from sqlalchemy import text
from src.database.session import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    # DB check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Redis check
    try:
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=3)
        r.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": overall,
        "services": {
            "api": "ok",
            "database": db_status,
            "redis": redis_status
        }
    }
