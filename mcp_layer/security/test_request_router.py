from mcp_layer.security.request_router import get_query_intent


queries = [
    "show my appointments",
    "show available doctors",
    "show my prescriptions",
    "show my medical history",
    "explain my medical history",
    "what should I do?",
    "hello"
]


for query in queries:
    intent = get_query_intent(query)

    print(f"Query: {query}")
    print(f"Intent: {intent}")
    print("-" * 40)