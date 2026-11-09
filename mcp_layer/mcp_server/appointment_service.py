from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import (
    Appointment,
    Doctor,
    DoctorSlot
)

def get_patient_appointments(patient_id: int):

    db = SessionLocal()

    try:
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.patient_id == patient_id
            )
            .order_by(
                Appointment.created_at.desc()
            )
            .all()
        )

        result = []

        for appointment in appointments:

            doctor = (
                db.query(Doctor)
                .filter(
                    Doctor.id == appointment.doctor_id
                )
                .first()
            )

            slot = (
                db.query(DoctorSlot)
                .filter(
                    DoctorSlot.id == appointment.slot_id
                )
                .first()
            )

            result.append({
                "appointment_id": appointment.id,
                "doctor_name": doctor.name if doctor else None,
                "specialization": (
                    doctor.specialization
                    if doctor
                    else None
                ),
                "date": (
                    str(slot.slot_date)
                    if slot
                    else None
                ),
                "time": (
                    str(slot.slot_time)
                    if slot
                    else None
                ),
                "status": appointment.status
            })

        return result

    finally:
        db.close()
def get_all_appointments():

    db = SessionLocal()

    try:
        appointments = (
            db.query(Appointment)
            .order_by(
                Appointment.created_at.desc()
            )
            .all()
        )

        result = []

        for appointment in appointments:

            doctor = (
                db.query(Doctor)
                .filter(
                    Doctor.id == appointment.doctor_id
                )
                .first()
            )

            slot = (
                db.query(DoctorSlot)
                .filter(
                    DoctorSlot.id == appointment.slot_id
                )
                .first()
            )

            result.append({
                "appointment_id": appointment.id,
                "patient_id": appointment.patient_id,
                "doctor_id": appointment.doctor_id,
                "doctor_name": doctor.name if doctor else None,
                "specialization": (
                    doctor.specialization
                    if doctor
                    else None
                ),
                "date": (
                    str(slot.slot_date)
                    if slot
                    else None
                ),
                "time": (
                    str(slot.slot_time)
                    if slot
                    else None
                ),
                "status": appointment.status
            })

        return result

    finally:
        db.close()