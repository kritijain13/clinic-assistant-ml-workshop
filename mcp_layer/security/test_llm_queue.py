import asyncio

from mcp_layer.security.llm_queue_service import (
    add_llm_request,
    run_llm_worker
)


async def fake_llm(request):

    print(f"START: {request}")

    await asyncio.sleep(2)

    print(f"END: {request}")

    return f"Response for {request}"


async def main():

    worker_task = asyncio.create_task(
        run_llm_worker(fake_llm)
    )

    for i in range(1, 6):

        result = await add_llm_request(
            f"Request-{i}"
        )

        print(result)

    await asyncio.sleep(11)

    worker_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())