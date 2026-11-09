from fastapi import APIRouter, Request, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from clinic_assistant.database.connection import get_db

from clinic_assistant.payments.service import (
    get_or_create_payment,
    create_razorpay_order,
    verify_razorpay_payment,
    get_payment_details,
    RAZORPAY_KEY_ID
)

from clinic_assistant.payments.receipt_service import generate_receipt

from src.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/payment",
    tags=["Payment"]
)


# ---------------------------------------------------------
# GET PAYMENT
# ---------------------------------------------------------

@router.get("/{appointment_id}")
async def get_payment(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    patient_id = request.session.get("patient_id")

    if not patient_id or request.session.get("role") != "USER":
        return {
            "success": False,
            "message": "Please login first."
        }

    payment, error = get_or_create_payment(
        appointment_id=appointment_id,
        patient_id=patient_id,
        db=db
    )

    if error:
        return {
            "success": False,
            "message": error
        }

    return {
        "success": True,
        "payment_id": payment.id,
        "appointment_id": payment.appointment_id,
        "amount": payment.amount,
        "payment_status": payment.payment_status
    }


# ---------------------------------------------------------
# CREATE RAZORPAY ORDER
# ---------------------------------------------------------

@router.post("/create-order")
async def create_order(
    request: Request,
    payment_data: dict,
    db: Session = Depends(get_db)
):

    patient_id = request.session.get("patient_id")

    if not patient_id or request.session.get("role") != "USER":
        return {
            "success": False,
            "message": "Please login first."
        }

    appointment_id = payment_data.get("appointment_id")

    if not appointment_id:
        return {
            "success": False,
            "message": "Appointment ID is required."
        }

    result, error = create_razorpay_order(
        appointment_id=int(appointment_id),
        patient_id=patient_id,
        db=db
    )

    if error:
        logger.error(error)

        return {
            "success": False,
            "message": error
        }

    return {
        "success": True,
        "key_id": RAZORPAY_KEY_ID,
        **result
    }


# ---------------------------------------------------------
# VERIFY RAZORPAY PAYMENT
# ---------------------------------------------------------

@router.post("/verify")
async def verify_payment(
    request: Request,
    payment_data: dict,
    db: Session = Depends(get_db)
):

    patient_id = request.session.get("patient_id")

    if not patient_id or request.session.get("role") != "USER":
        return {
            "success": False,
            "message": "Please login first."
        }

    payment_id = payment_data.get("payment_id")
    razorpay_order_id = payment_data.get("razorpay_order_id")
    razorpay_payment_id = payment_data.get("razorpay_payment_id")
    razorpay_signature = payment_data.get("razorpay_signature")

    if not all([
        payment_id,
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    ]):
        return {
            "success": False,
            "message": "Payment verification details are missing."
        }

    payment, error = verify_razorpay_payment(
        payment_id=int(payment_id),
        patient_id=patient_id,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        db=db
    )

    if error:
        logger.error(error)

        return {
            "success": False,
            "message": error
        }

    return {
        "success": True,
        "message": "Payment successful.",
        "payment_id": payment.id,
        "payment_status": payment.payment_status,
        "amount": payment.amount,
        "transaction_id": payment.transaction_id
    }


# ---------------------------------------------------------
# OLD DUMMY PAYMENT
# ---------------------------------------------------------
# Is route ko temporarily rakha hai.
# Frontend ab isko call nahi karega.

@router.post("/pay")
async def old_dummy_payment(
    request: Request,
    payment_data: dict,
    db: Session = Depends(get_db)
):

    return {
        "success": False,
        "message": "Dummy payment is disabled. Please use Razorpay."
    }


# ---------------------------------------------------------
# RECEIPT
# ---------------------------------------------------------

@router.get("/receipt/{payment_id}")
async def get_receipt(
    payment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    patient_id = request.session.get("patient_id")

    if not patient_id or request.session.get("role") != "USER":
        return {
            "success": False,
            "message": "Please login first."
        }

    details = get_payment_details(
        payment_id=payment_id,
        patient_id=patient_id,
        db=db
    )

    if not details:
        return {
            "success": False,
            "message": "Payment details not found."
        }

    payment = details["payment"]

    if payment.payment_status != "paid":
        return {
            "success": False,
            "message": "Payment has not been completed yet."
        }

    receipt_path = generate_receipt(details)

    return FileResponse(
        path=receipt_path,
        media_type="application/pdf",
        filename=f"payment_receipt_{payment_id}.pdf"
    )
