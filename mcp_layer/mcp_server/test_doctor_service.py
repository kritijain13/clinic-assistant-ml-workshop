from mcp_layer.mcp_server.doctor_service import (
    get_available_doctors,
    get_doctor_by_id,
    get_doctor_by_name,
    get_doctors_by_specialization
)


print("AVAILABLE DOCTORS")
print(get_available_doctors())


print("\nDOCTOR BY ID")
print(get_doctor_by_id(1))


print("\nDOCTOR BY NAME")
print(get_doctor_by_name("Dr. XYZ"))


print("\nDOCTOR BY SPECIALIZATION")
print(get_doctors_by_specialization("Cardiologist"))