
from sqlalchemy.orm import Session
from datetime import datetime
import os
import razorpay
from dotenv import load_dotenv

from clinic_assistant.database.models import (
    DoctorSlot,
    Appointment,
    Payment
)


# ============================================================
# Razorpay Configuration
# ============================================================

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


# ============================================================
# BOOK APPOINTMENT
# ============================================================

def book_appointment(
    patient_id: int,
    doctor_id: int,
    slot_id: int,
    reason: str,
    db: Session
):

    slot = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.id == slot_id,
            DoctorSlot.doctor_id == doctor_id
        )
        .first()
    )

    if not slot:

        return {
            "success": False,
            "message": "Selected slot does not exist."
        }

    if slot.is_booked:

        return {
            "success": False,
            "message": "This slot is already booked."
        }

    last_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id
        )
        .order_by(
            Appointment.token_number.desc()
        )
        .first()
    )

    if (
        last_appointment
        and last_appointment.token_number
    ):

        token_number = (
            last_appointment.token_number + 1
        )

    else:

        token_number = 1

    appointment = Appointment(

        patient_id=patient_id,

        doctor_id=doctor_id,

        slot_id=slot_id,

        reason=reason,

        status="booked",

        token_number=token_number
    )

    db.add(appointment)

    slot.is_booked = True

    try:

        db.commit()

        db.refresh(appointment)

        return {

            "success": True,

            "message": "Appointment booked successfully.",

            "appointment_id": appointment.id,

            "patient_id": patient_id,

            "doctor_id": doctor_id,

            "slot_id": slot_id,

            "reason": reason,

            "status": appointment.status,

            "token_number": appointment.token_number
        }

    except Exception:

        db.rollback()

        raise


# ============================================================
# CHECK IN APPOINTMENT
# ============================================================

def check_in_appointment(
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

        return {
            "success": False,
            "message": "Appointment not found."
        }

    if appointment.status != "booked":

        return {
            "success": False,
            "message": "This appointment cannot be checked in."
        }


    # ========================================================
    # ASSIGN TOKEN IF TOKEN IS MISSING
    # ========================================================

    if not appointment.token_number:

        last_checked_in_appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.status == "checked_in",
                Appointment.token_number.isnot(None)
            )
            .order_by(
                Appointment.token_number.desc()
            )
            .first()
        )

        last_booked_appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.token_number.isnot(None)
            )
            .order_by(
                Appointment.token_number.desc()
            )
            .first()
        )

        token_numbers = []

        if (
            last_checked_in_appointment
            and last_checked_in_appointment.token_number
        ):

            token_numbers.append(
                last_checked_in_appointment.token_number
            )

        if (
            last_booked_appointment
            and last_booked_appointment.token_number
        ):

            token_numbers.append(
                last_booked_appointment.token_number
            )

        if token_numbers:

            appointment.token_number = (
                max(token_numbers) + 1
            )

        else:

            appointment.token_number = 1


    # ========================================================
    # CHECK IN
    # ========================================================

    appointment.check_in_time = datetime.utcnow()

    appointment.status = "checked_in"

    try:

        db.commit()

        db.refresh(appointment)

        return {

            "success": True,

            "message": "Patient checked in successfully.",

            "appointment_id": appointment.id,

            "token_number": appointment.token_number,

            "check_in_time": appointment.check_in_time,

            "status": appointment.status
        }

    except Exception:

        db.rollback()

        raise


# ============================================================
# QUEUE STATUS
# ============================================================

def get_queue_status(
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

        return {
            "success": False,
            "message": "Appointment not found."
        }

    if appointment.status != "checked_in":

        return {
            "success": False,
            "message": "Please check in first."
        }


    if not appointment.token_number:

        last_appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.token_number.isnot(None)
            )
            .order_by(
                Appointment.token_number.desc()
            )
            .first()
        )

        if (
            last_appointment
            and last_appointment.token_number
        ):

            appointment.token_number = (
                last_appointment.token_number + 1
            )

        else:

            appointment.token_number = 1

        try:

            db.commit()

            db.refresh(appointment)

        except Exception:

            db.rollback()

            raise


    # ========================================================
    # PATIENTS AHEAD
    # ========================================================

    patients_ahead = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.status == "checked_in",
            Appointment.token_number.isnot(None),
            Appointment.token_number < appointment.token_number
        )
        .count()
    )


    queue_position = patients_ahead + 1


    # ========================================================
    # CURRENT PATIENT BEING SERVED
    # ========================================================

    current_patient = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.status == "checked_in",
            Appointment.token_number.isnot(None)
        )
        .order_by(
            Appointment.token_number.asc()
        )
        .first()
    )


    if current_patient:

        current_token = (
            current_patient.token_number
        )

    else:

        current_token = (
            appointment.token_number
        )


    # ========================================================
    # ESTIMATED WAIT TIME
    # ========================================================

    average_consultation_time = 10

    estimated_wait_time = (
        patients_ahead
        * average_consultation_time
    )


    return {

        "success": True,

        "appointment_id": appointment.id,

        "doctor_id": appointment.doctor_id,

        "token_number": appointment.token_number,

        "queue_position": queue_position,

        "patients_ahead": patients_ahead,

        "estimated_wait_time": estimated_wait_time,

        "current_token": current_token,

        "your_token": appointment.token_number,

        "status": appointment.status
    }


# ============================================================
# START CONSULTATION
# ============================================================

def start_consultation(
    appointment_id: int,
    db: Session
):

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:

        return {
            "success": False,
            "message": "Appointment not found."
        }

    if appointment.status != "checked_in":

        return {
            "success": False,
            "message": "Patient is not checked in."
        }

    appointment.status = "consulting"

    try:

        db.commit()

        db.refresh(appointment)

        return {

            "success": True,

            "message": "Consultation started.",

            "appointment_id": appointment.id,

            "doctor_id": appointment.doctor_id,

            "token_number": appointment.token_number,

            "status": appointment.status
        }

    except Exception:

        db.rollback()

        raise


# ============================================================
# COMPLETE CONSULTATION
# ============================================================

def complete_consultation(
    appointment_id: int,
    db: Session
):

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:

        return {
            "success": False,
            "message": "Appointment not found."
        }

    if appointment.status != "consulting":

        return {
            "success": False,
            "message": "Consultation is not currently running."
        }

    appointment.status = "completed"

    try:

        db.commit()

        db.refresh(appointment)

        return {

            "success": True,

            "message": "Consultation completed.",

            "appointment_id": appointment.id,

            "doctor_id": appointment.doctor_id,

            "token_number": appointment.token_number,

            "status": appointment.status
        }

    except Exception:

        db.rollback()

        raise


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

def cancel_appointment(
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

        return {
            "success": False,
            "message": "Appointment not found."
        }

    # Only BOOKED appointment can be cancelled.
    # Checked-in appointment cannot be cancelled/refunded.
    if appointment.status != "booked":

        return {
            "success": False,
            "message": "Only a booked appointment can be cancelled. A checked-in appointment cannot be cancelled."
        }

    slot = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.id == appointment.slot_id
        )
        .first()
    )

    appointment.status = "cancelled"

    if slot:

        slot.is_booked = False

    try:

        db.commit()

        db.refresh(appointment)

        return {

            "success": True,

            "message": "Appointment cancelled successfully.",

            "appointment_id": appointment.id,

            "patient_id": appointment.patient_id,

            "doctor_id": appointment.doctor_id,

            "slot_id": appointment.slot_id,

            "token_number": appointment.token_number,

            "status": appointment.status
        }

    except Exception:

        db.rollback()

        raise


# ============================================================
# CALCULATE REFUND
# ============================================================

def calculate_refund(
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

        return {
            "success": False,
            "message": "Appointment not found."
        }

    # ========================================================
    # ONLY BOOKED APPOINTMENT IS REFUNDABLE
    # ========================================================

    if appointment.status != "booked":

        return {
            "success": False,
            "message":
                "This appointment cannot be cancelled or refunded. "
                "A checked-in or completed appointment is not eligible for refund."
        }

    slot = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.id == appointment.slot_id
        )
        .first()
    )

    if not slot:

        return {
            "success": False,
            "message": "Appointment slot not found."
        }

    payment = (
        db.query(Payment)
        .filter(
            Payment.appointment_id == appointment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if not payment:

        return {
            "success": False,
            "message": "Payment record not found."
        }

    # ========================================================
    # ALREADY REFUNDED
    # ========================================================

    if payment.payment_status == "refunded":

        return {
            "success": False,
            "message": "This payment has already been refunded."
        }

    if payment.payment_status != "paid":

        return {
            "success": False,
            "message":
                "No refund available because payment is not successful."
        }

    if not payment.razorpay_payment_id:

        return {
            "success": False,
            "message": "Razorpay payment ID is missing."
        }

    appointment_datetime = datetime.combine(
        slot.slot_date,
        slot.slot_time
    )

    current_time = datetime.utcnow()

    hours_before_appointment = (
        appointment_datetime - current_time
    ).total_seconds() / 3600

    original_amount = float(payment.amount)

    if hours_before_appointment >= 24:

        deduction_percentage = 5

    else:

        deduction_percentage = 10

    deduction_amount = (
        original_amount
        * deduction_percentage
        / 100
    )

    refund_amount = (
        original_amount
        - deduction_amount
    )

    return {

        "success": True,

        "appointment_id": appointment.id,

        "payment_id": payment.id,

        "original_amount": original_amount,

        "deduction_percentage": deduction_percentage,

        "deduction_amount": round(
            deduction_amount,
            2
        ),

        "refund_amount": round(
            refund_amount,
            2
        ),

        "hours_before_appointment": round(
            hours_before_appointment,
            2
        ),

        "payment_status": payment.payment_status,

        "razorpay_payment_id":
            payment.razorpay_payment_id
    }


# ============================================================
# PROCESS REAL RAZORPAY REFUND
# ============================================================

def process_refund(
    appointment_id: int,
    patient_id: int,
    db: Session
):

    # ========================================================
    # STEP 1: FIND APPOINTMENT
    # ========================================================

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        )
        .first()
    )

    if not appointment:

        return {
            "success": False,
            "message": "Appointment not found."
        }

    # ========================================================
    # STEP 2: ONLY BOOKED APPOINTMENT CAN BE REFUNDED
    # ========================================================

    if appointment.status != "booked":

        return {
            "success": False,
            "message":
                "This appointment cannot be cancelled or refunded. "
                "A checked-in appointment cannot be cancelled or refunded."
        }

    # ========================================================
    # STEP 3: FIND PAYMENT
    # ========================================================

    payment = (
        db.query(Payment)
        .filter(
            Payment.appointment_id == appointment_id,
            Payment.patient_id == patient_id
        )
        .first()
    )

    if not payment:

        return {
            "success": False,
            "message": "Payment record not found."
        }

    # ========================================================
    # STEP 4: PREVENT DUPLICATE REFUND
    # ========================================================

    if payment.payment_status == "refunded":

        return {
            "success": False,
            "message": "This payment has already been refunded.",
            "razorpay_refund_id":
                payment.razorpay_refund_id
        }

    if payment.razorpay_refund_id:

        return {
            "success": False,
            "message":
                "A Razorpay refund already exists for this payment.",
            "razorpay_refund_id":
                payment.razorpay_refund_id
        }

    # ========================================================
    # STEP 5: PAYMENT MUST BE PAID
    # ========================================================

    if payment.payment_status != "paid":

        return {
            "success": False,
            "message":
                "Payment is not eligible for refund."
        }

    # ========================================================
    # STEP 6: RAZORPAY PAYMENT ID REQUIRED
    # ========================================================

    if not payment.razorpay_payment_id:

        return {
            "success": False,
            "message":
                "Razorpay payment ID is missing. "
                "Cannot process actual refund."
        }

    # ========================================================
    # STEP 7: CALCULATE REFUND
    # ========================================================

    refund_details = calculate_refund(
        appointment_id=appointment_id,
        patient_id=patient_id,
        db=db
    )

    if not refund_details.get("success"):

        return refund_details

    original_amount = float(
        refund_details["original_amount"]
    )

    deduction_percentage = float(
        refund_details["deduction_percentage"]
    )

    deduction_amount = float(
        refund_details["deduction_amount"]
    )

    refund_amount = float(
        refund_details["refund_amount"]
    )

    clinic_retained_amount = deduction_amount

    # ========================================================
    # STEP 8: CONVERT RUPEES TO PAISE
    # ========================================================

    refund_amount_paise = int(
        round(
            refund_amount * 100
        )
    )

    if refund_amount_paise <= 0:

        return {
            "success": False,
            "message":
                "Refund amount must be greater than zero."
        }

    # ========================================================
    # STEP 9: CALL ACTUAL RAZORPAY REFUND API
    # ========================================================

    try:

        logger_message = (
            f"Processing Razorpay refund. "
            f"appointment_id={appointment_id}, "
            f"patient_id={patient_id}, "
            f"payment_id={payment.razorpay_payment_id}, "
            f"refund_amount={refund_amount}"
        )

        print(logger_message)

        # ACTUAL RAZORPAY REFUND
        refund = razorpay_client.payment.refund(
            payment.razorpay_payment_id,
            {
                "amount": refund_amount_paise
            }
        )

        # ====================================================
        # STEP 10: GET RAZORPAY REFUND ID
        # ====================================================

        razorpay_refund_id = refund.get("id")

        if not razorpay_refund_id:

            db.rollback()

            return {
                "success": False,
                "message":
                    "Razorpay did not return a refund ID.",
                "razorpay_response":
                    str(refund)
            }

        # ====================================================
        # STEP 11: SAVE REFUND INFORMATION
        # ====================================================

        payment.deduction_percentage = (
            deduction_percentage
        )

        payment.deduction_amount = (
            deduction_amount
        )

        payment.refund_amount = (
            refund_amount
        )

        payment.clinic_retained_amount = (
            clinic_retained_amount
        )

        payment.razorpay_refund_id = (
            razorpay_refund_id
        )

        payment.transaction_id = (
            razorpay_refund_id
        )

        # ====================================================
        # STEP 12: UPDATE PAYMENT STATUS
        # ====================================================

        payment.payment_status = "refunded"

        payment.payment_date = datetime.utcnow()

        payment.refund_date = datetime.utcnow()

        # ====================================================
        # STEP 13: CANCEL APPOINTMENT
        # ====================================================

        appointment.status = "cancelled"

        # ====================================================
        # STEP 14: FREE SLOT
        # ====================================================

        slot = (
            db.query(DoctorSlot)
            .filter(
                DoctorSlot.id == appointment.slot_id
            )
            .first()
        )

        if slot:

            slot.is_booked = False

        # ====================================================
        # STEP 15: SAVE EVERYTHING
        # ====================================================

        db.commit()

        db.refresh(payment)

        db.refresh(appointment)

        # ====================================================
        # STEP 16: SUCCESS RESPONSE
        # ====================================================

        return {

            "success": True,

            "message":
                "Appointment cancelled and "
                "refund processed successfully.",

            "appointment_id":
                appointment_id,

            "payment_id":
                payment.id,

            "original_amount":
                original_amount,

            "deduction_percentage":
                deduction_percentage,

            "deduction_amount":
                deduction_amount,

            "refund_amount":
                refund_amount,

            "clinic_retained_amount":
                clinic_retained_amount,

            "razorpay_payment_id":
                payment.razorpay_payment_id,

            "razorpay_refund_id":
                razorpay_refund_id,

            "payment_status":
                payment.payment_status,

            "appointment_status":
                appointment.status
        }

    except Exception as e:

        db.rollback()

        print(
            f"Razorpay refund failed: {str(e)}"
        )

        return {

            "success": False,

            "message":
                "Razorpay refund failed.",

            "error":
                str(e)
        }

