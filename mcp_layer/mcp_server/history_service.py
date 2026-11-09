from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import MedicalHistory


def get_patient_history(patient_id: int):
    db = SessionLocal()

    try:
        history = db.query(MedicalHistory).filter(
            MedicalHistory.patient_id == patient_id
        ).all()

        result = []

        for record in history:
            result.append({
                "history_id": record.id,
                "patient_id": record.patient_id,
                "doctor_id": record.doctor_id,
                "problem": record.problem,
                "diagnosis": record.diagnosis,
                "visit_date": record.visit_date,
                "notes": record.notes
            })

        return result

    finally:
        db.close()