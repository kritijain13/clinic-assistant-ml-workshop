from mcp_layer.token_management.conversation_manager import (
    prepare_conversation
)


messages = []

for i in range(1, 13):

    messages.append({
        "role": "user",
        "content": f"Message {i}"
    })


result = prepare_conversation(messages)

print("Summarize Required:")
print(result["summarize_required"])

print("\nContext:")
print(result["context"])

print("\nSummary Prompt:")
print(result["summary_prompt"])