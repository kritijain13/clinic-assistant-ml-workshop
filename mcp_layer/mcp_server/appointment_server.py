from fastmcp import FastMCP

from mcp_layer.mcp_server.appointment_service import (
    get_patient_appointments
)

from mcp_layer.security.authorization import authorize


mcp = FastMCP("Appointment MCP")


@mcp.tool()
def get_my_appointments(
    patient_id: int,
    token: str
):
    """
    Get appointments for a patient after permission check.
    """

    auth = authorize(
        token,
        "appointment:read"
    )

    if not auth["allowed"]:
        return auth

    # Token ke user ko sirf apne appointments dekhne denge
    if auth["user_id"] != patient_id:
        return {
            "allowed": False,
            "message": "You can only access your own appointments."
        }

    appointments = get_patient_appointments(
        patient_id
    )

    if not appointments:
        return {
            "allowed": True,
            "success": False,
            "message": "No appointments found."
        }

    return {
        "allowed": True,
        "success": True,
        "appointments": appointments
    }


if __name__ == "__main__":
    mcp.run()