from datetime import datetime


token_usage_logs = []


def log_token_usage(
    user_id: int,
    tool_name: str,
    input_tokens: int,
    output_tokens: int,
    cost: float = 0.0
):
    total_tokens = input_tokens + output_tokens

    log = {
        "user_id": user_id,
        "tool_name": tool_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
        "timestamp": datetime.now().isoformat()
    }

    token_usage_logs.append(log)

    return log


def get_user_usage(user_id: int):

    return [
        log
        for log in token_usage_logs
        if log["user_id"] == user_id
    ]