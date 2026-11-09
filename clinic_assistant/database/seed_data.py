from datetime import date, timedelta, time

from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import Doctor, DoctorSlot

from src.logger import get_logger


logger = get_logger(__name__)


def seed_doctors():

    db = SessionLocal()

    try:

        doctors_data = [
            {
                "name": "Dr. Suresh Sharma",
                "specialization": "Gastroenterologist",
                "experience_years": 12,
                "phone": "9876543210",
                "email": "suresh@clinic.com",
            },
            {
                "name": "Dr. Neha Verma",
                "specialization": "Neurologist",
                "experience_years": 10,
                "phone": "9876543211",
                "email": "neha@clinic.com",
            },
            {
                "name": "Dr. Amit Singh",
                "specialization": "Orthopedic",
                "experience_years": 8,
                "phone": "9876543212",
                "email": "amit@clinic.com",
            },
            {
                "name": "Dr. Priya Sharma",
                "specialization": "Dermatologist",
                "experience_years": 7,
                "phone": "9876543213",
                "email": "priya@clinic.com",
            },
            {
                "name": "Dr. Rahul Mehta",
                "specialization": "General Physician",
                "experience_years": 15,
                "phone": "9876543214",
                "email": "rahul@clinic.com",
            },
        ]

        doctors = []

        for doctor_data in doctors_data:

            doctor = db.query(Doctor).filter(
                Doctor.email == doctor_data["email"]
            ).first()

            if not doctor:

                doctor = Doctor(**doctor_data)

                db.add(doctor)
                db.flush()

                doctors.append(doctor)

                logger.info(f"Doctor added: {doctor.name}")

            else:

                doctors.append(doctor)

        db.commit()

        print("Doctors added successfully!")

        slot_times = [
            time(10, 0),
            time(11, 0),
            time(12, 0),
            time(15, 0),
            time(16, 0),
        ]

        for doctor in doctors:

            for day_number in range(1, 4):

                slot_date = date.today() + timedelta(days=day_number)

                for slot_time in slot_times:

                    existing_slot = db.query(DoctorSlot).filter(
                        DoctorSlot.doctor_id == doctor.id,
                        DoctorSlot.slot_date == slot_date,
                        DoctorSlot.slot_time == slot_time
                    ).first()

                    if not existing_slot:

                        slot = DoctorSlot(
                            doctor_id=doctor.id,
                            slot_date=slot_date,
                            slot_time=slot_time,
                            is_booked=False
                        )

                        db.add(slot)

        db.commit()

        logger.info("Doctor slots added successfully")

        print("Doctor slots added successfully!")

    except Exception as e:

        db.rollback()

        logger.error(f"Doctor seed data failed: {str(e)}")

        print("Doctor data insertion failed!")
        print(e)

    finally:

        db.close()


if __name__ == "__main__":
    seed_doctors()