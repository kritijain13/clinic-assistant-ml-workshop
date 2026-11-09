from mcp_layer.auth.auth_service import create_access_token

from mcp_layer.mcp_server.doctor_server import (
    get_available_doctors_tool,
    get_doctor_by_id_tool,
    get_doctor_by_name_tool,
    get_doctors_by_specialization_tool
)


# Create valid JWT
token = create_access_token(
    user_id=501,
    role="USER"
)

print("JWT CREATED")
print(token)


print("\nAVAILABLE DOCTORS")
result = get_available_doctors_tool(token)

print(result)


print("\nDOCTOR BY ID")
result = get_doctor_by_id_tool(
    doctor_id=1,
    token=token
)

print(result)


print("\nDOCTOR BY NAME - FAKE DOCTOR")
result = get_doctor_by_name_tool(
    name="Dr. XYZ",
    token=token
)

print(result)


print("\nDOCTORS BY SPECIALIZATION")
result = get_doctors_by_specialization_tool(
    specialization="Cardiologist",
    token=token
)

print(result)