from mcp_layer.mcp_server.history_service import (
    get_patient_history
)


print("PATIENT MEDICAL HISTORY")

result = get_patient_history(1)

print(result)