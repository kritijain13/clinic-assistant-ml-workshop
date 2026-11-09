import asyncio
from mcp_layer.llm.groq_client import get_groq_client
from mcp_layer.security.request_queue import (
    request_queue,
    process_llm_request
)
from mcp_layer.token_management.cost_controller import (
    check_budget,
    record_llm_usage,
    record_actual_llm_usage
)
from mcp_layer.token_management.conversation_manager import (
    prepare_conversation
)

from mcp_layer.token_management.cost_controller import (
    check_budget,
    record_llm_usage
)


async def add_llm_request(
    user_id: int,
    query: str,
    messages,
    summary=None
):

    # 1. Estimate tokens before sending to LLM
    estimated_tokens = 1000

    # 2. Check user's token budget
    budget = check_budget(
        user_id,
        estimated_tokens
    )

    if not budget["allowed"]:
        return {
            "status": "budget_exhausted",
            "message": budget["message"]
        }

    # 3. Prepare conversation context
    conversation_data = prepare_conversation(
        messages,
        summary
    )

    # 4. Create LLM request
    request = {
        "user_id": user_id,
        "query": query,
        "context": conversation_data["context"],
        "summarize_required": conversation_data["summarize_required"],
        "summary_prompt": conversation_data["summary_prompt"]
    }

    # 5. Put request into queue
    await request_queue.put(request)

    return {
        "status": "queued",
        "message": "Your request has been added to the queue.",
        "summarize_required": conversation_data["summarize_required"]
    }


async def run_llm_worker(llm_function):

    while True:

        request = await request_queue.get()

        try:

            # 6. Call LLM
            result = await process_llm_request(
                llm_function,
                request
            )

            # 7. Record actual usage
            output_text = result.choices[0].message.content

            usage = result.usage

            print("LLM Result:", output_text)

            print("Actual Groq Usage:")
            print("Input tokens:", usage.prompt_tokens)
            print("Output tokens:", usage.completion_tokens)
            print("Total tokens:", usage.total_tokens)
            saved_usage = record_actual_llm_usage(
            user_id=request["user_id"],
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens
            )

            print("Saved Usage:")
            print(saved_usage)


        finally:

            request_queue.task_done()

async def call_groq(request):

    client = get_groq_client()

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": request["query"]
            }
        ],
        max_completion_tokens=300,
        reasoning_effort="low"
    )

    return response
