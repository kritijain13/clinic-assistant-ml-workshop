from sqlalchemy.orm import Session

from clinic_assistant.database.models import DoctorSlot


def get_available_slots(
    doctor_id: int,
    db: Session
):

    slots = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.doctor_id == doctor_id,
            DoctorSlot.is_booked == False
        )
        .order_by(
            DoctorSlot.slot_date,
            DoctorSlot.slot_time
        )
        .all()
    )

    result = []

    for slot in slots:

        result.append(
            {
                "id": slot.id,
                "date": str(slot.slot_date),
                "time": str(slot.slot_time)
            }
        )

    return result