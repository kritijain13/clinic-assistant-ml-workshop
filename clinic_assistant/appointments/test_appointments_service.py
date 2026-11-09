from clinic_assistant.database.connection import SessionLocal

from clinic_assistant.appointments.appointments_service import (
    book_appointment
)


db = SessionLocal()


try:

    result = book_appointment(

        patient_id=1,

        doctor_id=2,

        slot_id=16,

        reason="Headache and dizziness",

        db=db
    )


    print("\nAppointment Result:\n")

    print(result)


finally:

    db.close()