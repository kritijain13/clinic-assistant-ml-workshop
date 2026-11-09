from clinic_assistant.database.connection import SessionLocal

from clinic_assistant.appointments.slot_service import (
    get_available_slots
)


db = SessionLocal()

try:

    slots = get_available_slots(
        doctor_id=2,
        db=db
    )

    print("\nAvailable Slots:\n")

    for slot in slots:

        print(slot)

finally:

    db.close()