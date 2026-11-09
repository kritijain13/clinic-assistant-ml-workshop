
from fastmcp import FastMCP

from mcp_layer.security.authorization import authorize

from mcp_layer.mcp_server.history_service import (
    get_patient_history
)


mcp = FastMCP("History MCP")


@mcp.tool()
def get_my_history(patient_id: int, token: str):

    auth = authorize(token, "history:read")

    if not auth["allowed"]:
        return auth

    if auth["user_id"] != patient_id:
        return {
            "allowed": False,
            "status": "forbidden",
            "message": "You can only access your own medical history."
        }

    history = get_patient_history(patient_id)

    if not history:
        return {
            "status": "not_found",
            "message": "No medical history found for this patient."
        }

    return {
        "status": "success",
        "history": history
    }


if __name__ == "__main__":
    mcp.run()

