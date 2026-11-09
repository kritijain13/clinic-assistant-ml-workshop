from mcp_layer.token_management.token_budget import (
    can_use_tokens,
    add_token_usage,
    get_usage_status
)
from mcp_layer.token_management.token_usage_service import save_token_usage
from mcp_layer.token_management.token_counter import (
    calculate_total_tokens
)

from mcp_layer.token_management.token_usage_logger import (
    log_token_usage
)


def check_budget(user_id: int, estimated_tokens: int):

    allowed = can_use_tokens(
        user_id,
        estimated_tokens
    )

    if not allowed:
        return {
            "allowed": False,
            "message": "Your usage limit has been reached. Upgrade to continue."
        }

    usage = get_usage_status(user_id)

    return {
        "allowed": True,
        "status": usage["status"],
        "remaining_tokens": usage["remaining_tokens"]
    }


def record_llm_usage(
    user_id: int,
    tool_name: str,
    input_text: str,
    output_text: str,
    cost: float = 0.0
):

    token_data = calculate_total_tokens(
        input_text,
        output_text
    )

    total_tokens = token_data["total_tokens"]

    add_token_usage(
        user_id,
        total_tokens
    )

    log_token_usage(
        user_id=user_id,
        tool_name=tool_name,
        input_tokens=token_data["input_tokens"],
        output_tokens=token_data["output_tokens"],
        cost=cost
    )

    return token_data
def record_actual_llm_usage(
    user_id: int,
    input_tokens: int,
    output_tokens: int,
    cost: float = 0.0
):
    return save_token_usage(
        user_id=user_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost
    )