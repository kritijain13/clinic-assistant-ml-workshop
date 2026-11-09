from mcp_layer.token_management.token_usage_service import (
    save_token_usage,
    get_today_usage
)


user_id = 99

print("Before adding usage:")
print(get_today_usage(user_id))


print("\nAdding 500 tokens...")

result = save_token_usage(
    user_id=user_id,
    input_tokens=300,
    output_tokens=200,
    cost=0.01
)

print(result)


print("\nToday's usage:")
print(get_today_usage(user_id))