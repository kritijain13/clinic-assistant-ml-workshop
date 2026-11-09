from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import Doctor


def get_available_doctors():

    db = SessionLocal()

    try:
        doctors = (
            db.query(Doctor)
            .filter(Doctor.available == True)
            .all()
        )

        result = []

        for doctor in doctors:
            result.append({
                "doctor_id": doctor.id,
                "name": doctor.name,
                "email": doctor.email,
                "specialization": doctor.specialization,
                "location": doctor.location,
                "experience_years": doctor.experience_years,
                "consultation_fee": doctor.consultation_fee,
                "available": doctor.available
            })

        return result

    finally:
        db.close()


def get_doctor_by_id(doctor_id: int):

    db = SessionLocal()

    try:
        doctor = (
            db.query(Doctor)
            .filter(Doctor.id == doctor_id)
            .filter(Doctor.available == True)
            .first()
        )

        if not doctor:
            return None

        return {
            "doctor_id": doctor.id,
            "name": doctor.name,
            "specialization": doctor.specialization,
            "location": doctor.location,
            "experience_years": doctor.experience_years,
            "consultation_fee": doctor.consultation_fee,
            "available": doctor.available
        }

    finally:
        db.close()


def get_doctor_by_name(name: str):

    db = SessionLocal()

    try:
        doctor = (
            db.query(Doctor)
            .filter(
                Doctor.name.ilike(name),
                Doctor.available == True
            )
            .first()
        )

        if not doctor:
            return None

        return {
            "doctor_id": doctor.id,
            "name": doctor.name,
            "specialization": doctor.specialization,
            "location": doctor.location,
            "experience_years": doctor.experience_years,
            "consultation_fee": doctor.consultation_fee,
            "available": doctor.available
        }

    finally:
        db.close()


def get_doctors_by_specialization(specialization: str):

    db = SessionLocal()

    try:
        doctors = (
            db.query(Doctor)
            .filter(
                Doctor.specialization.ilike(
                    f"%{specialization}%"
                ),
                Doctor.available == True
            )
            .all()
        )

        result = []

        for doctor in doctors:
            result.append({
                "doctor_id": doctor.id,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "location": doctor.location,
                "experience_years": doctor.experience_years,
                "consultation_fee": doctor.consultation_fee,
                "available": doctor.available
            })

        return result

    finally:
        db.close()
def get_all_doctors():

    db = SessionLocal()

    try:
        doctors = db.query(Doctor).all()

        result = []

        for doctor in doctors:
            result.append({
                "doctor_id": doctor.id,
                "name": doctor.name,
                "email": doctor.email,
                "specialization": doctor.specialization,
                "location": doctor.location,
                "experience_years": doctor.experience_years,
                "consultation_fee": doctor.consultation_fee,
                "available": doctor.available
            })

        return result

    finally:
        db.close()
