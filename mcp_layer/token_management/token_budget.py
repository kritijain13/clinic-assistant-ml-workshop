from mcp_layer.token_management.token_usage_service import (
    get_today_usage,
    save_token_usage
)


USER_DAILY_TOKEN_LIMIT = 10000

WARNING_THRESHOLD = 0.80


def get_used_tokens(user_id: int):
    usage = get_today_usage(user_id)

    return usage["total_tokens"]


def get_remaining_tokens(user_id: int):
    used_tokens = get_used_tokens(user_id)

    remaining = USER_DAILY_TOKEN_LIMIT - used_tokens

    return max(remaining, 0)


def can_use_tokens(user_id: int, estimated_tokens: int):

    remaining = get_remaining_tokens(user_id)

    if estimated_tokens > remaining:
        return False

    return True


def add_token_usage(user_id: int, tokens: int):

    save_token_usage(
        user_id=user_id,
        input_tokens=0,
        output_tokens=tokens,
        cost=0.0
    )


def get_usage_status(user_id: int):

    used_tokens = get_used_tokens(user_id)

    remaining_tokens = get_remaining_tokens(user_id)

    usage_percentage = used_tokens / USER_DAILY_TOKEN_LIMIT

    if usage_percentage >= 1:
        status = "EXHAUSTED"

    elif usage_percentage >= WARNING_THRESHOLD:
        status = "WARNING"

    else:
        status = "NORMAL"

    return {
        "user_id": user_id,
        "daily_limit": USER_DAILY_TOKEN_LIMIT,
        "used_tokens": used_tokens,
        "remaining_tokens": remaining_tokens,
        "usage_percentage": usage_percentage,
        "status": status
    }