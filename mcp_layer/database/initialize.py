"""Narrow, idempotent initialization for MCP token usage storage."""

from mcp_layer.database.connection import engine
from mcp_layer.database.models import TokenUsage


def initialize_token_usage_table() -> None:
    """Create only the token usage table if it does not already exist."""
    TokenUsage.__table__.create(bind=engine, checkfirst=True)
