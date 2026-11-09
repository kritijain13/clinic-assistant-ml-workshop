from datetime import date, timedelta

from mcp_layer.database.connection import SessionLocal
from mcp_layer.database.models import TokenUsage
from mcp_layer.token_management.token_budget import (
    get_used_tokens,
    get_remaining_tokens
)


user_id = 100

db = SessionLocal()

try:
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Yesterday ki usage create karo
    old_usage = TokenUsage(
        user_id=user_id,
        usage_date=yesterday,
        input_tokens=4000,
        output_tokens=4000,
        total_tokens=8000,
        cost=0.10
    )

    db.add(old_usage)
    db.commit()

finally:
    db.close()


print("Yesterday's usage: 8000 tokens")

print("\nToday's usage:")
print("Used:", get_used_tokens(user_id))
print("Remaining:", get_remaining_tokens(user_id))