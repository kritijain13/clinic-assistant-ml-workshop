from groq import Groq
from dotenv import load_dotenv
import os

from mcp_layer.token_management.token_usage_service import save_token_usage


load_dotenv("clinic_assistant/.env")


def get_groq_client():

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not set")

    client = Groq(api_key=api_key)

    return client


def ask_groq(
    user_id: int,
    prompt: str,
    context: str = ""
):

    client = get_groq_client()

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a clinic assistant, not a doctor. Do not diagnose or "
                    "prescribe. Use supplied clinic records only when relevant, "
                    "say when records do not contain the answer, and recommend "
                    "urgent local care for emergencies. Never disclose or infer "
                    "another patient's records. Never invent a doctor, clinic, "
                    "availability, or appointment; provider facts must appear in "
                    "the supplied database context. If no provider is present there, "
                    "say none could be confirmed."
                )
            },
            {
                "role": "user",
                "content": f"Clinic records from MCP (may be empty):\n{context}\n\nQuestion: {prompt}"
            }
        ],
        max_completion_tokens=300,
        reasoning_effort="low"
    )

    usage = response.usage

    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens

    save_token_usage(
        user_id=user_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=0.0
    )

    return {
        "response": response.choices[0].message.content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }
