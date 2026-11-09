from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import Patient


def get_all_patients():

    db = SessionLocal()

    try:
        patients = db.query(Patient).all()

        result = []

        for patient in patients:
            result.append({
                "patient_id": patient.id,
                "name": patient.name,
                "email": patient.email,
                "phone": patient.phone,
                "created_at": (
                    patient.created_at.isoformat()
                    if patient.created_at
                    else None
                )
            })

        return result

    finally:
        db.close()