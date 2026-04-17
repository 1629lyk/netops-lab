"""
models.py — SQLAlchemy table definitions
Tables: config_backups, compliance_results
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime
)
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class ConfigBackup(Base):
    __tablename__ = "config_backups"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    hostname    = Column(String(64), nullable=False, index=True)
    filepath    = Column(String(256), nullable=False)
    backed_up_at= Column(DateTime, default=lambda: datetime.now(timezone.utc))
    success     = Column(Boolean, nullable=False)
    lines       = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<ConfigBackup host={self.hostname} at={self.backed_up_at} ok={self.success}>"


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    hostname    = Column(String(64), nullable=False, index=True)
    policy      = Column(String(128), nullable=False)
    passed      = Column(Boolean, nullable=False)
    detail      = Column(Text, nullable=True)
    checked_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ComplianceResult host={self.hostname} policy={self.policy} passed={self.passed}>"
