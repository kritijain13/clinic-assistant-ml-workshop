from mcp_layer.mcp_server.prescription_service import (
    get_patient_prescriptions
)


print("PATIENT PRESCRIPTIONS")

result = get_patient_prescriptions(1)

print(result)