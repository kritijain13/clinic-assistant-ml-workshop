from mcp_layer.token_management.token_usage_service import (
    save_token_usage,
    get_today_usage
)


print("Saving first usage...")

result = save_token_usage(
    user_id=1,
    input_tokens=500,
    output_tokens=300,
    cost=0.01
)

print(result)


print("\nSaving second usage...")

result = save_token_usage(
    user_id=1,
    input_tokens=200,
    output_tokens=100,
    cost=0.005
)

print(result)


print("\nToday's usage...")

usage = get_today_usage(user_id=1)

print(usage)
def get_all_users_usage():

    from mcp_layer.database.connection import SessionLocal
    from mcp_layer.database.models import TokenUsage

    db = SessionLocal()

    try:
        usages = (
            db.query(TokenUsage)
            .order_by(TokenUsage.usage_date.desc())
            .all()
        )

        result = []

        for usage in usages:
            result.append({
                "user_id": usage.user_id,
                "usage_date": str(usage.usage_date),
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "cost": usage.cost
            })

        return result

    finally:
        db.close()