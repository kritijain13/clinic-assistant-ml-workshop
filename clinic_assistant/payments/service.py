import uuid
from datetime import datetime

import os
import razorpay
from dotenv import load_dotenv

from sqlalchemy.orm import Session

from clinic_assistant.database.models import (
    Payment,
    Appointment,
    Patient,
    Doctor,
    DoctorSlot
)


# ---------------------------------------------------------
# ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


# ---------------------------------------------------------
# RAZORPAY CLIENT
# ---------------------------------------------------------

razorpay_client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


# ---------------------------------------------------------
# CONSULTATION FEE
# ---------------------------------------------------------

CONSULTATION_FEE = 500.0


# ---------------------------------------------------------
# GET OR CREATE PAYMENT
# ---------------------------------------------------------

def get_or_create_payment(
    appointment_id: int,
    patient_id: int,
    db: Session
):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        )
        .first()
    )

    if not appointment:
        return None, "Appointment not found."

    payment = (
        db.query(Payment)
        .filter(
            Payment.appointment_id == appointment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if payment:
        return payment, None

    payment = Payment(
        appointment_id=appointment_id,
        patient_id=patient_id,
        amount=CONSULTATION_FEE,
        payment_status="pending"
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment, None


# ---------------------------------------------------------
# CREATE RAZORPAY ORDER
# ---------------------------------------------------------

def create_razorpay_order(
    appointment_id: int,
    patient_id: int,
    db: Session
):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        )
        .first()
    )

    if not appointment:
        return None, "Appointment not found."

    payment = (
        db.query(Payment)
        .filter(
            Payment.appointment_id == appointment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if not payment:
        payment = Payment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            amount=CONSULTATION_FEE,
            payment_status="pending"
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

    # -----------------------------------------------------
    # If already paid
    # -----------------------------------------------------

    if payment.payment_status == "paid":

        return {
            "payment_id": payment.id,
            "amount": int(payment.amount * 100),
            "currency": "INR",
            "payment_status": payment.payment_status,
            "razorpay_order_id": payment.razorpay_order_id
        }, None

    # -----------------------------------------------------
    # If Razorpay order already exists
    # -----------------------------------------------------

    if payment.razorpay_order_id:

        return {
            "payment_id": payment.id,
            "amount": int(payment.amount * 100),
            "currency": "INR",
            "payment_status": payment.payment_status,
            "razorpay_order_id": payment.razorpay_order_id
        }, None

    # -----------------------------------------------------
    # Create new Razorpay order
    # -----------------------------------------------------

    order_data = {
        "amount": int(payment.amount * 100),
        "currency": "INR",
        "receipt": f"appointment_{appointment_id}",
        "notes": {
            "appointment_id": str(appointment_id),
            "patient_id": str(patient_id)
        }
    }

    try:

        order = razorpay_client.order.create(
            data=order_data
        )

    except Exception as error:

        return None, f"Unable to create Razorpay order: {str(error)}"

    # -----------------------------------------------------
    # Save Razorpay order ID
    # -----------------------------------------------------

    payment.razorpay_order_id = order["id"]

    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "amount": order["amount"],
        "currency": order["currency"],
        "razorpay_order_id": order["id"],
        "payment_status": payment.payment_status
    }, None


# ---------------------------------------------------------
# VERIFY RAZORPAY PAYMENT
# ---------------------------------------------------------

def verify_razorpay_payment(
    payment_id: int,
    patient_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session
):
    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if not payment:
        return None, "Payment not found."

    # -----------------------------------------------------
    # Already paid
    # -----------------------------------------------------

    if payment.payment_status == "paid":
        return payment, None

    # -----------------------------------------------------
    # Check order ID
    # -----------------------------------------------------

    if payment.razorpay_order_id != razorpay_order_id:

        return None, "Razorpay order ID does not match."


    # -----------------------------------------------------
    # Verify Razorpay signature
    # -----------------------------------------------------

    try:

        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature
            }
        )

    except Exception:

        return None, "Payment verification failed."


    # -----------------------------------------------------
    # Payment verified successfully
    # -----------------------------------------------------

    payment.razorpay_order_id = razorpay_order_id

    payment.razorpay_payment_id = razorpay_payment_id

    payment.razorpay_signature = razorpay_signature

    payment.payment_status = "paid"

    # We can use Razorpay payment ID as transaction ID
    payment.transaction_id = razorpay_payment_id

    payment.payment_date = datetime.utcnow()

    db.commit()
    db.refresh(payment)

    return payment, None


# ---------------------------------------------------------
# OLD DUMMY PAYMENT
# ---------------------------------------------------------
# Keeping this temporarily so your old API does not break.
# After Razorpay testing is successful, we can remove it.
# ---------------------------------------------------------

def process_dummy_payment(
    payment_id: int,
    patient_id: int,
    db: Session
):
    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if not payment:
        return None, "Payment not found."

    if payment.payment_status == "paid":
        return payment, None

    transaction_id = (
        f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-"
        f"{uuid.uuid4().hex[:8].upper()}"
    )

    payment.payment_status = "paid"

    payment.transaction_id = transaction_id

    payment.payment_date = datetime.utcnow()

    db.commit()
    db.refresh(payment)

    return payment, None


# ---------------------------------------------------------
# GET PAYMENT DETAILS
# ---------------------------------------------------------

def get_payment_details(
    payment_id: int,
    patient_id: int,
    db: Session
):
    result = (
        db.query(
            Payment,
            Appointment,
            Patient,
            Doctor,
            DoctorSlot
        )
        .join(
            Appointment,
            Payment.appointment_id == Appointment.id
        )
        .join(
            Patient,
            Payment.patient_id == Patient.id
        )
        .join(
            Doctor,
            Appointment.doctor_id == Doctor.id
        )
        .join(
            DoctorSlot,
            Appointment.slot_id == DoctorSlot.id
        )
        .filter(
            Payment.id == payment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if not result:
        return None

    payment, appointment, patient, doctor, slot = result

    return {
        "payment": payment,
        "appointment": appointment,
        "patient": patient,
        "doctor": doctor,
        "slot": slot
    }