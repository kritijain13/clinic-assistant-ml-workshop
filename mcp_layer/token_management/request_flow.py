from mcp_layer.security.request_router import get_query_intent
from mcp_layer.security.llm_queue_service import (
    add_llm_request
)
from mcp_layer.token_management.duplicate_detector import (
    is_duplicate_request
)

from mcp_layer.token_management.cache import (
    get_cache,
    set_cache
)

from mcp_layer.token_management.cost_controller import (
    check_budget
)

async def process_request(
    user_id: int,
    query: str,
    messages=None,
    summary=None
):

    # Step 1: Duplicate check
    if is_duplicate_request(user_id, query):
        return {
            "status": "duplicate",
            "message": "Duplicate request detected."
        }

    # Step 2: Cache check
    cached_response = get_cache(query)

    if cached_response is not None:
        return {
            "status": "cache",
            "response": cached_response
        }

    # Step 3: Intent detection
    intent = get_query_intent(query)

    # Step 4: Simple query → MCP
    if intent != "llm":

        return {
            "status": "mcp",
            "intent": intent,
            "llm_required": False
        }

    # Step 5: Complex query → budget check
    estimated_tokens = 1000

    budget = check_budget(
        user_id,
        estimated_tokens
    )

    if not budget["allowed"]:
        return {
            "status": "budget_exhausted",
            "message": budget["message"]
        }

    # Step 6: LLM
  # Step 6: Add request to LLM queue
    # Step 6: Add request to LLM queue
    queue_result = await add_llm_request(
        user_id=user_id,
        query=query,
        messages=messages or [],
        summary=summary
    )

    return {
        "status": "llm",
        "intent": intent,
        "llm_required": True,
        "remaining_tokens": budget["remaining_tokens"],
        "queue": queue_result
    }