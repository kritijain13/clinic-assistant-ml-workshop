from datetime import date

from mcp_layer.database.connection import SessionLocal
from mcp_layer.database.models import TokenUsage


def save_token_usage(
    user_id: int,
    input_tokens: int,
    output_tokens: int,
    cost: float = 0.0
):
    db = SessionLocal()

    try:
        today = date.today()

        usage = (
            db.query(TokenUsage)
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.usage_date == today
            )
            .first()
        )

        if usage:
            usage.input_tokens += input_tokens
            usage.output_tokens += output_tokens
            usage.total_tokens += input_tokens + output_tokens
            usage.cost += cost

        else:
            usage = TokenUsage(
                user_id=user_id,
                usage_date=today,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost=cost
            )

            db.add(usage)

        db.commit()
        db.refresh(usage)

        return {
            "user_id": usage.user_id,
            "usage_date": str(usage.usage_date),
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "cost": usage.cost
        }

    finally:
        db.close()


def get_today_usage(user_id: int):
    db = SessionLocal()

    try:
        today = date.today()

        usage = (
            db.query(TokenUsage)
            .filter(
                TokenUsage.user_id == user_id,
                TokenUsage.usage_date == today
            )
            .first()
        )

        if not usage:
            return {
                "user_id": user_id,
                "usage_date": str(today),
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0
            }

        return {
            "user_id": usage.user_id,
            "usage_date": str(usage.usage_date),
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "cost": usage.cost
        }

    finally:
        db.close()
def get_all_users_usage():

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