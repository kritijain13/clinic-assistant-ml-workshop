"""Shared database bindings for MCP token usage.

TokenUsage keeps its own declarative Base, while using the clinic application's
TiDB engine and session factory.
"""

from clinic_assistant.database.connection import SessionLocal, engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

__all__ = ["engine", "SessionLocal", "Base"]
