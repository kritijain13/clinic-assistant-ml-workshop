
from mcp_layer.auth.auth_service import create_access_token

from mcp_layer.mcp_server.prescription_server import (
    get_my_prescriptions
)


# Create token for User 1
token = create_access_token(
    user_id=1,
    role="USER"
)

print("JWT CREATED")
print(token)


# Test 1: User 1 accessing Patient 1
print("\nTEST 1: User 1 -> Patient 1")

result = get_my_prescriptions(
    patient_id=1,
    token=token
)

print(result)


# Test 2: User 1 accessing Patient 2
print("\nTEST 2: User 1 -> Patient 2")

result = get_my_prescriptions(
    patient_id=2,
    token=token
)

print(result)

