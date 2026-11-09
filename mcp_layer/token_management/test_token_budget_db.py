from mcp_layer.token_management.token_budget import (
    get_used_tokens,
    get_remaining_tokens,
    can_use_tokens,
    add_token_usage,
    get_usage_status
)


user_id = 1

print("Before usage:")

print("Used:", get_used_tokens(user_id))
print("Remaining:", get_remaining_tokens(user_id))

print("\nAdding 1000 tokens...")

add_token_usage(user_id, 1000)

print("\nAfter usage:")

print("Used:", get_used_tokens(user_id))
print("Remaining:", get_remaining_tokens(user_id))

print("\nCan use 500 tokens?")
print(can_use_tokens(user_id, 500))

print("\nUsage status:")

print(get_usage_status(user_id))