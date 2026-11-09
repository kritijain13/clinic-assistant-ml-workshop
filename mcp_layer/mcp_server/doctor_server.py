from fastmcp import FastMCP

from mcp_layer.security.authorization import authorize

from mcp_layer.mcp_server.doctor_service import (
    get_available_doctors,
    get_doctor_by_id,
    get_doctor_by_name,
    get_doctors_by_specialization
)


mcp = FastMCP("Doctor MCP")


@mcp.tool()
def get_available_doctors_tool(token: str):

    auth = authorize(token, "doctor:read")
    if not auth["allowed"]:
        return auth

    doctors = get_available_doctors()

    if not doctors:
        return {
            "status": "not_found",
            "message": "No available doctors are listed in the clinic database."
        }

    return {
        "status": "success",
        "doctors": doctors
    }


@mcp.tool()
def get_doctor_by_id_tool(
    doctor_id: int,
    token: str
):

    auth = authorize(token, "doctor:read")
    if not auth["allowed"]:
        return auth

    doctor = get_doctor_by_id(doctor_id)

    if not doctor:
        return {
            "status": "not_found",
            "message": "Doctor not found in the database."
        }

    return {
        "status": "success",
        "doctor": doctor
    }


@mcp.tool()
def get_doctor_by_name_tool(
    name: str,
    token: str
):

    auth = authorize(token, "doctor:read")
    if not auth["allowed"]:
        return auth

    doctor = get_doctor_by_name(name)

    if not doctor:
        return {
            "status": "not_found",
            "message": "Doctor not found in the database."
        }

    return {
        "status": "success",
        "doctor": doctor
    }


@mcp.tool()
def get_doctors_by_specialization_tool(
    specialization: str,
    token: str
):

    auth = authorize(token, "doctor:read")
    if not auth["allowed"]:
        return auth

    doctors = get_doctors_by_specialization(
        specialization
    )

    if not doctors:
        return {
            "status": "not_found",
            "message": "No doctors found for this specialization."
        }

    return {
        "status": "success",
        "doctors": doctors
    }


if __name__ == "__main__":
    mcp.run()
