import asyncio

MAX_QUEUE_SIZE = 100

request_queue = asyncio.Queue(
    maxsize=MAX_QUEUE_SIZE
)

llm_semaphore = asyncio.Semaphore(1)


async def add_request(request):
    await request_queue.put(request)


async def get_request():
    request = await request_queue.get()
    return request


async def process_llm_request(llm_function, request):
    async with llm_semaphore:
        result = await llm_function(request)

    return result