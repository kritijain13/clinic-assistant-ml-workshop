from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import Prescription


def get_patient_prescriptions(patient_id: int):

    db = SessionLocal()

    try:

        prescriptions = db.query(Prescription).filter(
            Prescription.patient_id == patient_id
        ).all()

        result = []

        for prescription in prescriptions:

            result.append({
                "prescription_id": prescription.id,
                "patient_id": prescription.patient_id,
                "original_filename": prescription.original_filename,
                "saved_filename": prescription.saved_filename,
                "file_path": prescription.file_path,
                "doctor_name": prescription.doctor_name,
                "patient_name": prescription.patient_name,
                "prescription_date": prescription.prescription_date,
                "diagnosis": prescription.diagnosis,
                "instructions": prescription.instructions,
                "follow_up": prescription.follow_up,
                "medicines": prescription.medicines,
                "created_at": prescription.created_at
            })

        return result

    finally:
        db.close()