
from fastmcp import FastMCP

from mcp_layer.security.authorization import authorize

from mcp_layer.mcp_server.prescription_service import (
    get_patient_prescriptions
)


mcp = FastMCP("Prescription MCP")


@mcp.tool()
def get_my_prescriptions(patient_id: int, token: str):

    auth = authorize(token, "history:read")

    if not auth["allowed"]:
        return auth

    if auth["user_id"] != patient_id:
        return {
            "allowed": False,
            "status": "forbidden",
            "message": "You can only access your own prescriptions."
        }

    prescriptions = get_patient_prescriptions(patient_id)

    if not prescriptions:
        return {
            "status": "not_found",
            "message": "No prescriptions found for this patient."
        }

    return {
        "status": "success",
        "prescriptions": prescriptions
    }


if __name__ == "__main__":
    mcp.run()

