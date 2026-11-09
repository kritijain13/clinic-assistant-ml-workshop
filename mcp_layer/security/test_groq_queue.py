import asyncio

from mcp_layer.security.llm_queue_service import (
    add_llm_request,
    run_llm_worker,
    call_groq
)


async def main():

    # Add request to queue
    result = await add_llm_request(
        user_id=500,
        query="What is machine learning? Explain simply.",
        messages=[
            {
                "role": "user",
                "content": "What is machine learning?"
            }
        ]
    )

    print("Queue Result:")
    print(result)

    # Start worker
    worker_task = asyncio.create_task(
        run_llm_worker(call_groq)
    )

    # Wait until queue request is processed
    await asyncio.sleep(10)

    # Stop worker after testing
    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass


asyncio.run(main())