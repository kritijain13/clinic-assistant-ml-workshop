import asyncio

from mcp_layer.security.llm_queue_service import (
    run_llm_worker,
    call_groq
)


async def start_mcp_layer():

    print("MCP Layer starting...")

    worker_task = asyncio.create_task(
        run_llm_worker(call_groq)
    )

    print("LLM worker started.")

    await worker_task


if __name__ == "__main__":
    asyncio.run(start_mcp_layer())