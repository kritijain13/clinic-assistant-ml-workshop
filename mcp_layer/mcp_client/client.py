import asyncio
import sys
import json
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from mcp_layer.auth.token import generate_token
from mcp_layer.security.request_router import get_query_intent, is_other_patient_data_request
from mcp_layer.llm.groq_client import ask_groq


async def call_appointment_mcp(patient_id: int, token: str):

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_layer.mcp_server.appointment_server"]
    )

    client = Client(transport)

    async with client:
        result = await client.call_tool(
            "get_my_appointments",
            {
                "patient_id": patient_id,
                "token": token
            }
        )

        return result


async def call_doctor_mcp(token: str):

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_layer.mcp_server.doctor_server"]
    )

    client = Client(transport)

    async with client:
        result = await client.call_tool(
            "get_available_doctors_tool",
            {
                "token": token
            }
        )

        return result


async def call_prescription_mcp(patient_id: int, token: str):

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_layer.mcp_server.prescription_server"]
    )

    client = Client(transport)

    async with client:
        result = await client.call_tool(
            "get_my_prescriptions",
            {
                "patient_id": patient_id,
                "token": token
            }
        )

        return result


async def call_history_mcp(patient_id: int, token: str):

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_layer.mcp_server.history_server"]
    )

    client = Client(transport)

    async with client:
        result = await client.call_tool(
            "get_my_history",
            {
                "patient_id": patient_id,
                "token": token
            }
        )

        return result


async def get_patient_history_context(patient_id: int):
    """Fetch the current patient's clinical history through the History MCP tool."""
    token = generate_token(user_id=patient_id, role="USER")["access_token"]
    result = await call_history_mcp(patient_id, token)
    return result.content[0].text if result.content else "No MCP history was returned."


async def process_query(query: str, patient_id: int, role: str = "USER"):

    auth_data = generate_token(
        user_id=patient_id,
        role=role
    )

    token = auth_data["access_token"]

    intent = get_query_intent(query)

    lowered_query = query.casefold()
    if "doctor" in lowered_query and any(term in lowered_query for term in (
        "create", "add", "register", "insert", "make a doctor"
    )):
        return {
            "success": False,
            "message": "I can't create doctor profiles. I can only search doctors already listed in the clinic database."
        }
    if is_other_patient_data_request(query, patient_id):
        return {
            "success": False,
            "message": "I can only help with your own clinic records. I can't access or share another patient's details."
        }

    if role != "USER" and intent in {"appointment", "prescription", "history"}:
        return {
            "success": False,
            "message": "Patient-specific MCP records are available only to the signed-in patient."
        }

    print("\nUser Query:", query)
    print("Intent:", intent)

    # Appointment MCP
    if intent == "appointment":

        print("Route: Appointment MCP")
        print("LLM bypassed.")

        result = await call_appointment_mcp(
            patient_id,
            token
        )

        print("\nMCP Response:")
        print(result)

        return json.loads(result.content[0].text)

    # Doctor MCP
    if intent == "doctor":

        print("Route: Doctor MCP")
        print("LLM bypassed.")

        result = await call_doctor_mcp(
            token
        )

        print("\nMCP Response:")
        print(result)

        return json.loads(result.content[0].text)

    # Prescription MCP
    if intent == "prescription":

        print("Route: Prescription MCP")
        print("LLM bypassed.")

        result = await call_prescription_mcp(
            patient_id,
            token
        )

        print("\nMCP Response:")
        print(result)

        return json.loads(result.content[0].text)

    # History MCP
    if intent == "history":

        print("Route: History MCP")
        print("LLM bypassed.")

        result = await call_history_mcp(
            patient_id,
            token
        )

        print("\nMCP Response:")
        print(result)

        return json.loads(result.content[0].text)

    # Complex query
    if intent == "llm":
        print("Route: MCP context + LLM")
        context = ""
        # Give the LLM the signed-in user's history via MCP, rather than
        # allowing it to invent clinical facts from an ungrounded prompt.
        if role == "USER":
            try:
                history = await call_history_mcp(patient_id, token)
                context = history.content[0].text if history.content else ""
            except Exception as exc:
                print(f"MCP history context unavailable: {exc}")
        if "doctor" in lowered_query:
            try:
                doctor_result = await call_doctor_mcp(token)
                doctor_text = doctor_result.content[0].text if doctor_result.content else ""
                context += f"\nAvailable doctors from the clinic database MCP tool:\n{doctor_text}"
            except Exception as exc:
                print(f"MCP doctor lookup unavailable: {exc}")
        result = await asyncio.to_thread(
            ask_groq, patient_id, query, context
        )
        return {
            "success": True,
            "response": result["response"],
            "source": "mcp_llm",
            "usage": {
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "total_tokens": result["total_tokens"]
            }
        }
async def main():

    await process_query(
        "show my appointments",
        1
    )

    await process_query(
        "available doctors",
        1
    )

    await process_query(
        "show my prescription",
        1
    )

    await process_query(
        "show my medical history",
        1
    )

    await process_query(
        "Please summarize my medical history",
        1
    )


if __name__ == "__main__":
    asyncio.run(main())
