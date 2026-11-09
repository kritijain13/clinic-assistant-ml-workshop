import asyncio

from mcp_layer.security.request_queue import (
    request_queue,
    process_llm_request
)


async def fake_llm(request):

    print(f"START: {request}")

    await asyncio.sleep(2)

    print(f"END: {request}")

    return f"Response for {request}"


async def worker():

    while True:

        request = await request_queue.get()

        try:
            result = await process_llm_request(
                fake_llm,
                request
            )

            print(result)

        finally:
            request_queue.task_done()


async def main():

    worker_task = asyncio.create_task(
        worker()
    )

    for i in range(1, 6):

        await request_queue.put(
            f"Request-{i}"
        )

    await request_queue.join()

    worker_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())