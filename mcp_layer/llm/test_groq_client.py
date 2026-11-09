from mcp_layer.llm.groq_client import ask_groq


result = ask_groq(
    user_id=1,
    prompt="What is machine learning? Explain in one simple sentence."
)

print("Response:")
print(result["response"])

print("\nUsage:")
print("Input tokens:", result["input_tokens"])
print("Output tokens:", result["output_tokens"])
print("Total tokens:", result["total_tokens"])