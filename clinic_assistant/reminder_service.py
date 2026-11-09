import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.email_service import send_appointment_reminder
from clinic_assistant.database.models import Appointment, Patient, Doctor, DoctorSlot

from apscheduler.schedulers.background import BackgroundScheduler


def send_pending_reminders():
    db = SessionLocal()

    try:
        now = datetime.now()

        reminder_start = now + timedelta(hours=23, minutes=55)
        reminder_end = now + timedelta(hours=24, minutes=5)

        appointments = (
            db.query(Appointment)
            .join(DoctorSlot, Appointment.slot_id == DoctorSlot.id)
            .filter(
                Appointment.status == "booked",
                Appointment.reminder_sent == False
            )
            .all()
        )

        print(f"Found {len(appointments)} booked appointments")

        # Appointment ki date/time check karne ke liye
        for appointment in appointments:
            slot = db.query(DoctorSlot).filter(
                DoctorSlot.id == appointment.slot_id
            ).first()

            print(
                "Appointment:",
                appointment.id,
                "Date:",
                slot.slot_date,
                "Time:",
                slot.slot_time
            )

        for appointment in appointments:

            patient = db.query(Patient).filter(
                Patient.id == appointment.patient_id
            ).first()

            doctor = db.query(Doctor).filter(
                Doctor.id == appointment.doctor_id
            ).first()

            slot = db.query(DoctorSlot).filter(
                DoctorSlot.id == appointment.slot_id
            ).first()

            appointment_datetime = datetime.combine(
                slot.slot_date,
                slot.slot_time
            )

            # Sirf 24 hours ke aas-paas wale appointments
            if reminder_start <= appointment_datetime <= reminder_end:

                print("Appointment found for reminder:")
                print("Appointment ID:", appointment.id)
                print("Patient:", patient.name)
                print("Email:", patient.email)
                print("Doctor:", doctor.name)
                print("Specialization:", doctor.specialization)
                print("Date:", slot.slot_date)
                print("Time:", slot.slot_time)
                print("----------------------------")

                # Reminder email send
                send_appointment_reminder(
                    patient_email=patient.email,
                    patient_name=patient.name,
                    appointment_id=appointment.id,
                    doctor_name=doctor.name,
                    specialization=doctor.specialization,
                    appointment_date=slot.slot_date,
                    appointment_time=slot.slot_time
                )

                # Email successfully send hone ke baad SQL me save
                appointment.reminder_sent = True
                db.commit()

                print("Reminder email sent successfully")

    finally:
        db.close()


# Automatic scheduler
scheduler = BackgroundScheduler()

scheduler.add_job(
    send_pending_reminders,
    "interval",
    minutes=5,
    next_run_time=datetime.now()
)

print("Scheduler jobs:", scheduler.get_jobs())