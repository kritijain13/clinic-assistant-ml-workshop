import asyncio

from mcp_layer.token_management.request_flow import process_request
from mcp_layer.security.llm_queue_service import (
    run_llm_worker,
    call_groq
)


async def main():

    # Start LLM worker
    worker_task = asyncio.create_task(
        run_llm_worker(call_groq)
    )

    # Send request through request flow
    result = await process_request(
        user_id=501,
        query="Explain machine learning in simple words.",
        messages=[
            {
                "role": "user",
                "content": "Explain machine learning in simple words."
            }
        ]
    )

    print("Request Flow Result:")
    print(result)

    # Give worker time to process request
    await asyncio.sleep(10)

    # Stop worker
    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass


asyncio.run(main())