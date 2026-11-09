import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

FROM_EMAIL = os.getenv("REMINDER_FROM_EMAIL")


def send_appointment_reminder(
    patient_email,
    patient_name,
    appointment_id,
    doctor_name,
    specialization,
    appointment_date,
    appointment_time
):
    subject = "Appointment Reminder - Sanjeevani"

    html = f"""
    <h2>Appointment Reminder</h2>

    <p>Hello {patient_name},</p>

    <p>This is a reminder for your upcoming appointment.</p>

    <p>
        <b>Appointment ID:</b> {appointment_id}<br>
        <b>Doctor:</b> {doctor_name}<br>
        <b>Specialization:</b> {specialization}<br>
        <b>Date:</b> {appointment_date}<br>
        <b>Time:</b> {appointment_time}
    </p>

    <p>Please arrive on time.</p>

    <p>Thank you,<br>Sanjeevani Clinic</p>
    """

    response = resend.Emails.send({
        "from": FROM_EMAIL,
        "to":  ["kritijain1308@gmail.com"],
        "subject": subject,
        "html": html
    })

    return response