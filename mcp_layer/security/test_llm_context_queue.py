import asyncio

from mcp_layer.security.llm_queue_service import (
    add_llm_request,
    run_llm_worker
)

from mcp_layer.token_management.token_budget import (
    get_usage_status
)


async def fake_llm(request):

    print("\n--- LLM REQUEST ---")

    print("Query:")
    print(request["query"])

    print("\nContext:")
    print(request["context"])

    await asyncio.sleep(2)

    return "Fake LLM response"


async def main():

    worker_task = asyncio.create_task(
        run_llm_worker(fake_llm)
    )

    messages = []

    for i in range(1, 13):

        messages.append({
            "role": "user",
            "content": f"Message {i}"
        })

    result = await add_llm_request(
        user_id=1,
        query="Please summarize my medical history",
        messages=messages
    )

    print("\nQueue Response:")
    print(result)

    await asyncio.sleep(3)

    print("\nUsage After LLM:")
    print(get_usage_status(1))

    worker_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())