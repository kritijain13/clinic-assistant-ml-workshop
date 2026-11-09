from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.appointments.doctor_service import (
    get_doctors_by_specialization
)


db = SessionLocal()

try:

    doctors = get_doctors_by_specialization(
        specialization="Neurologist",
        db=db
    )

    print("\nAvailable Neurologists:\n")

    for doctor in doctors:

        print(doctor)

finally:

    db.close()