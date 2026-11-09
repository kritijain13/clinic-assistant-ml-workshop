from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.history.service import get_patient_history


db = SessionLocal()

try:
    patient_id = 1

    history = get_patient_history(
        patient_id=patient_id,
        db=db
    )

    print("\nPatient History:")
    print(history)

finally:
    db.close()