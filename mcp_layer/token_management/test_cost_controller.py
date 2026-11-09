from mcp_layer.token_management.cost_controller import (
    check_budget,
    record_llm_usage
)


user_id = 203


print("1. Initial budget:")
print(check_budget(user_id, 1000))


print("\n2. Adding 8000 tokens...")

result = record_llm_usage(
    user_id=user_id,
    tool_name="LLM",
    input_text="a" * 32000,
    output_text="",
    cost=0.01
)

print("Recorded usage:", result)


print("\n3. Budget after 8000 tokens:")
print(check_budget(user_id, 1000))