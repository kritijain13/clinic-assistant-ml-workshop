from sqlalchemy.orm import Session

from clinic_assistant.database.models import Doctor


# =========================================================
# GET DOCTORS BY SPECIALIZATION
# =========================================================

def get_doctors_by_specialization(
    specialization: str,
    db: Session,
    location: str = None
):

    query = (
        db.query(Doctor)
        .filter(
            Doctor.specialization.ilike(
                specialization
            ),
            Doctor.available == True
        )
    )

    # LOCATION FILTER
    if location:
        query = query.filter(
            Doctor.location.ilike(location)
        )

    doctors = query.all()

    result = []

    for doctor in doctors:

        result.append(
            {
                "id": doctor.id,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "location": doctor.location,
                "experience_years": doctor.experience_years,
                "phone": doctor.phone,
                "email": doctor.email,
                "consultation_fee": float(
                    doctor.consultation_fee
                    if doctor.consultation_fee is not None
                    else 0
                )
            }
        )

    return result


# =========================================================
# GET ALL AVAILABLE DOCTORS
# =========================================================

def get_all_available_doctors(
    db: Session,
    location: str = None
):

    query = (
        db.query(Doctor)
        .filter(
            Doctor.available == True
        )
    )

    # LOCATION FILTER
    if location:
        query = query.filter(
            Doctor.location.ilike(location)
        )

    doctors = query.all()

    result = []

    for doctor in doctors:

        result.append(
            {
                "id": doctor.id,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "location": doctor.location,
                "experience_years": doctor.experience_years,
                "phone": doctor.phone,
                "email": doctor.email,
                "consultation_fee": float(
                    doctor.consultation_fee
                    if doctor.consultation_fee is not None
                    else 0
                )
            }
        )

    return result