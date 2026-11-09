from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from clinic_assistant.appointments.slot_service import (
    get_available_slots
)

from clinic_assistant.appointments.appointments_service import (
    book_appointment,
    check_in_appointment,
    get_queue_status,
    start_consultation,
    complete_consultation,
    calculate_refund,
    process_refund
)

from clinic_assistant.appointments.schemas import (
    AppointmentRequest
)

from clinic_assistant.database.connection import get_db

from clinic_assistant.database.models import (
    Appointment,
    Doctor,
    DoctorSlot,
    Patient
)

from clinic_assistant.appointments.doctor_service import (
    get_doctors_by_specialization,
    get_all_available_doctors
)

from src.logger import get_logger


logger = get_logger(__name__)


router = APIRouter(
    prefix="/api",
    tags=["Appointments"]
)


def doctor_owns_appointment(request: Request, appointment_id: int, db: Session) -> bool:
    if request.session.get("role") != "DOCTOR":
        return False
    account_id = request.session.get("patient_id")
    account = db.query(Patient).filter(
        Patient.id == account_id,
        Patient.role == "DOCTOR"
    ).first()
    if not account:
        return False
    doctor = db.query(Doctor).filter(Doctor.email == account.email).first()
    if not doctor:
        return False
    return db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == doctor.id
    ).first() is not None


# ---------------------------------------------------------
# GET DOCTORS BY SPECIALIZATION
# ---------------------------------------------------------

@router.get("/doctors")
async def get_doctors(
    specialization: str,
    location: str = None,
    db: Session = Depends(get_db)
):

    try:

        doctors = get_doctors_by_specialization(
            specialization=specialization,
            location=location,
            db=db
        )

        return {
            "success": True,
            "specialization": specialization,
            "location": location,
            "doctors": doctors
        }

    except Exception as e:

        logger.error(
            f"Doctor search error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to fetch doctors."
        }


# ---------------------------------------------------------
# GET ALL AVAILABLE DOCTORS
# ---------------------------------------------------------

@router.get("/available-doctors")
async def get_available_doctors(
    location: str = None,
    db: Session = Depends(get_db)
):

    try:

        doctors = get_all_available_doctors(
            location=location,
            db=db
        )

        return {
            "success": True,
            "location": location,
            "doctors": doctors
        }

    except Exception as e:

        logger.error(
            f"Available doctor search error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to fetch available doctors."
        }


# ---------------------------------------------------------
# GET AVAILABLE SLOTS
# ---------------------------------------------------------

@router.get("/slots")
async def get_slots(
    doctor_id: int,
    db: Session = Depends(get_db)
):

    try:

        slots = get_available_slots(
            doctor_id=doctor_id,
            db=db
        )

        return {
            "success": True,
            "doctor_id": doctor_id,
            "slots": slots
        }

    except Exception as e:

        logger.error(
            f"Slot search error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to fetch available slots."
        }


# ---------------------------------------------------------
# GET MY APPOINTMENTS
# ---------------------------------------------------------

@router.get("/appointments/my")
async def get_my_appointments(
    request: Request,
    db: Session = Depends(get_db)
):

    try:

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

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

                "doctor_id": appointment.doctor_id,

                "doctor_name":
                    doctor.name
                    if doctor else "Unknown",

                "specialization":
                    doctor.specialization
                    if doctor else "Unknown",

                "slot_id": appointment.slot_id,

                "date":
                    str(slot.slot_date)
                    if slot else None,

                "time":
                    str(slot.slot_time)
                    if slot else None,

                "reason":
                    appointment.reason,

                "status":
                    appointment.status,

                "token_number":
                    appointment.token_number,

                "check_in_time":
                    str(appointment.check_in_time)
                    if appointment.check_in_time
                    else None,

                "created_at":
                    str(appointment.created_at)
                    if appointment.created_at
                    else None
            })

        return {
            "success": True,
            "appointments": result
        }

    except Exception as e:

        logger.error(
            f"My appointments error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to fetch appointments."
        }


# ---------------------------------------------------------
# BOOK APPOINTMENT
# ---------------------------------------------------------

@router.post("/appointments")
async def create_appointment(
    request: Request,
    appointment_request: AppointmentRequest,
    db: Session = Depends(get_db)
):

    try:

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        result = book_appointment(
            patient_id=patient_id,
            doctor_id=appointment_request.doctor_id,
            slot_id=appointment_request.slot_id,
            reason=appointment_request.reason,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Appointment booking error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to book appointment."
        }


@router.post("/appointments/check-in")
async def check_in(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):

    try:

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        result = check_in_appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Appointment check-in error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to check in."
        }


@router.get("/appointments/queue")
async def queue_status(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):
    try:

        patient_id = request.session.get("patient_id")

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        result = get_queue_status(
            appointment_id=appointment_id,
            patient_id=patient_id,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Queue status error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to fetch queue status."
        }


# ============================================================
# STEP 7: Start Consultation
# ============================================================

@router.post("/appointments/start-consultation")
async def start_doctor_consultation(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):
    try:
        if not doctor_owns_appointment(request, appointment_id, db):
            return {"success": False, "message": "Doctor access denied for this appointment."}

        result = start_consultation(
            appointment_id=appointment_id,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Start consultation error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to start consultation."
        }


# ============================================================
# STEP 7: Complete Consultation
# ============================================================

@router.post("/appointments/complete-consultation")
async def complete_doctor_consultation(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):
    try:
        if not doctor_owns_appointment(request, appointment_id, db):
            return {"success": False, "message": "Doctor access denied for this appointment."}

        result = complete_consultation(
            appointment_id=appointment_id,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Complete consultation error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to complete consultation."
        }


# ============================================================
# STEP 8: Cancel Appointment
# ============================================================

# ============================================================
# CANCEL APPOINTMENT + REAL RAZORPAY REFUND
# ============================================================

@router.post("/appointments/cancel")
async def cancel_patient_appointment(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):

    try:

        # ----------------------------------------------------
        # GET LOGGED-IN PATIENT
        # ----------------------------------------------------

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        # ----------------------------------------------------
        # IMPORTANT:
        # DO NOT call cancel_appointment()
        #
        # process_refund() will:
        # 1. calculate refund
        # 2. call Razorpay
        # 3. save refund ID
        # 4. mark payment refunded
        # 5. cancel appointment
        # 6. free slot
        # ----------------------------------------------------

        logger.info(
            f"Cancellation + refund requested. "
            f"patient_id={patient_id}, "
            f"appointment_id={appointment_id}"
        )

        result = process_refund(
            appointment_id=appointment_id,
            patient_id=patient_id,
            db=db
        )

        # ----------------------------------------------------
        # REFUND SUCCESS
        # ----------------------------------------------------

        if result.get("success"):

            logger.info(
                f"Cancellation + refund successful. "
                f"patient_id={patient_id}, "
                f"appointment_id={appointment_id}, "
                f"razorpay_refund_id="
                f"{result.get('razorpay_refund_id')}"
            )

            return {

                "success": True,

                "message":
                    "Appointment cancelled and "
                    "Razorpay refund processed successfully.",

                "appointment_id":
                    appointment_id,

                "original_amount":
                    result.get("original_amount"),

                "deduction_percentage":
                    result.get("deduction_percentage"),

                "deduction_amount":
                    result.get("deduction_amount"),

                "refund_amount":
                    result.get("refund_amount"),

                "clinic_retained_amount":
                    result.get("clinic_retained_amount"),

                "razorpay_payment_id":
                    result.get("razorpay_payment_id"),

                "razorpay_refund_id":
                    result.get("razorpay_refund_id"),

                "payment_status":
                    result.get("payment_status"),

                "appointment_status":
                    result.get("appointment_status")
            }

        # ----------------------------------------------------
        # REFUND FAILED
        # ----------------------------------------------------

        logger.warning(
            f"Cancellation/refund failed. "
            f"patient_id={patient_id}, "
            f"appointment_id={appointment_id}, "
            f"message={result.get('message')}"
        )

        return {

            "success": False,

            "message":
                result.get(
                    "message",
                    "Appointment was not cancelled and refund was not processed."
                ),

            "error":
                result.get("error")
        }

    except Exception as e:

        db.rollback()

        logger.exception(
            f"Appointment cancellation/refund error. "
            f"patient_id="
            f"{request.session.get('patient_id')}, "
            f"appointment_id={appointment_id}: "
            f"{str(e)}"
        )

        return {

            "success": False,

            "message":
                "Appointment was not cancelled "
                "and refund was not processed.",

            "error":
                str(e)
        }


@router.get("/appointments/refund")
async def refund_details(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):
    try:

        patient_id = request.session.get("patient_id")

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        result = calculate_refund(
            appointment_id=appointment_id,
            patient_id=patient_id,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Refund calculation error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to calculate refund."
        }


# ============================================================
# STEP 9: Process Refund
# ============================================================

@router.post("/appointments/refund")
async def process_appointment_refund(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db)
):
    try:

        patient_id = request.session.get("patient_id")

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        result = process_refund(
            appointment_id=appointment_id,
            patient_id=patient_id,
            db=db
        )

        return result

    except Exception as e:

        logger.error(
            f"Refund processing error: {str(e)}"
        )

        return {
            "success": False,
            "message": "Unable to process refund."
        }
