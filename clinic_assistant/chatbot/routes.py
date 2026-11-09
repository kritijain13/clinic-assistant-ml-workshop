from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from clinic_assistant.chatbot.service import get_chat_response
from mcp_layer.mcp_client.client import get_patient_history_context
from mcp_layer.security.request_router import get_query_intent, is_other_patient_data_request

from clinic_assistant.appointments.appointments_service import (
    check_in_appointment,
    get_queue_status,
    calculate_refund,
    process_refund
)

from clinic_assistant.chatbot.schemas import ChatRequest

from clinic_assistant.database.connection import get_db

from clinic_assistant.history.service import (
    get_patient_history,
    get_chat_history,
    save_chat
)

from clinic_assistant.appointments.doctor_service import (
    get_doctors_by_specialization,
    get_all_available_doctors
)

from clinic_assistant.database.models import (
    Appointment,
    Doctor,
    DoctorSlot
)

from src.logger import get_logger
from mcp_layer.token_management.token_budget import (
    USER_DAILY_TOKEN_LIMIT,
    get_usage_status,
)


logger = get_logger(__name__)

# One active chat request per signed-in patient in this app process.
_active_chat_patients: set[int] = set()


router = APIRouter(
    prefix="/api",
    tags=["Chatbot"]
)


# =========================================================
# CONFIRMATION WORDS
# =========================================================

CONFIRMATION_WORDS = {
    "yes",
    "yeah",
    "yep",
    "yup",
    "sure",
    "ok",
    "okay",
    "yes please",
    "sure please",
    "go ahead",
    "please",
    "show doctors",
    "check doctors",
    "find doctors",
    "check the doctors",
    "show available doctors"
}


# =========================================================
# APPOINTMENT WORDS
# =========================================================

APPOINTMENT_WORDS = {
    "i need an appointment",
    "i need appointment",
    "i need a appointment",
    "i want an appointment",
    "i want appointment",
    "i want a appointment",
    "i want to book an appointment",
    "i want to book appointment",
    "i need to book an appointment",
    "i need to book appointment",
    "book an appointment",
    "book appointment",
    "i need to see a doctor",
    "i want to see a doctor",
    "i want to consult a doctor",
    "i need to consult a doctor",
    "i want a doctor appointment",
    "i need a doctor appointment",
    "schedule an appointment",
    "schedule appointment",
    "make an appointment",
    "make appointment",
    "book a doctor",
    "book doctor"
}


# =========================================================
# SHOW APPOINTMENTS WORDS
# =========================================================

SHOW_APPOINTMENTS_WORDS = {
    "show my appointments",
    "show my appointment",
    "show appointments",
    "show appointment",
    "my appointments",
    "my appointment",
    "appointments",
    "appointment",
    "all",
    "all appointments",
    "show all appointments",
    "show all appointment",
    "list appointments",
    "list my appointments",
    "view appointments",
    "view my appointments",
    "check my appointments",
    "check appointments",
    "show my appointmnets",
    "show appointmnets",
    "my appointmnets"
}


# =========================================================
# CHECK-IN WORDS
# =========================================================

CHECK_IN_WORDS = {
    "check in",
    "check-in",
    "check me in",
    "checkin",
    "i want to check in",
    "i need to check in",
    "i want check in",
    "i need check in"
}


# =========================================================
# CHECK QUEUE WORDS
# =========================================================

CHECK_QUEUE_WORDS = {
    "check queue",
    "queue",
    "my queue",
    "check my queue",
    "queue status",
    "check queue status",
    "what is my queue",
    "where am i in queue"
}


# =========================================================
# CANCELLATION WORDS
# =========================================================

CANCEL_WORDS = {
    "cancel my appointment",
    "cancel appointment",
    "cancel my appointment please",

    "i want to cancel my appointment",
    "i need to cancel my appointment",

    "i want to cancel appointment",
    "i need to cancel appointment",

    "i want cancel appointment",
    "i need cancel appointment",

    "cancel my booking",
    "cancel booking",

    "i want to cancel my booking",
    "i need to cancel my booking",

    "i want cancel this appointment",
    "i need cancel this appointment",

    "i want to cancel this appointment",
    "i need to cancel this appointment"
}


# =========================================================
# CANCEL DECLINE WORDS
# =========================================================

CANCEL_DECLINE_WORDS = {
    "no",
    "no thanks",
    "keep appointment",
    "keep it",
    "don't cancel",
    "do not cancel",
    "dont cancel"
}


# =========================================================
# REFUND WORDS
# =========================================================

REFUND_WORDS = {
    "refund",
    "process refund",
    "get refund",
    "i want refund",
    "i want a refund",
    "refund please",
    "process my refund"
}


# =========================================================
# HELPER - CLEAR CANCEL SESSION
# =========================================================

def clear_cancel_session(request: Request):

    request.session.pop(
        "cancel_selection_pending",
        None
    )

    request.session.pop(
        "cancel_confirmation_pending",
        None
    )

    request.session.pop(
        "cancel_pending_appointment_id",
        None
    )


# =========================================================
# HELPER - COMMON RESPONSE
# =========================================================

def chat_response(
    response_text,
    specialization=None,
    needs_doctor=False,
    needs_confirmation=False,
    needs_appointment=False,
    doctors=None
):

    return {
        "success": True,
        "response": response_text,
        "specialization": specialization,
        "needs_doctor": needs_doctor,
        "needs_confirmation": needs_confirmation,
        "needs_appointment": needs_appointment,
        "doctors": doctors or []
    }


# =========================================================
# CHATBOT
# =========================================================

@router.post("/chat")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    patient_id = None
    chat_slot_acquired = False
    try:

        # =====================================================
        # MESSAGE
        # =====================================================

        message = chat_request.message.strip()

        if not message:

            return {
                "success": False,
                "message": "Please enter a message."
            }


        # =====================================================
        # LOGIN CHECK
        # =====================================================

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }

        # No await occurs between checking and marking the slot, so concurrent
        # requests in this worker cannot both start LLM/MCP processing.
        if patient_id in _active_chat_patients:
            return {
                "success": False,
                "busy": True,
                "message": "Your previous message is still being processed. Please wait for its reply before sending another one."
            }
        _active_chat_patients.add(patient_id)
        chat_slot_acquired = True

        if is_other_patient_data_request(message, patient_id):
            refusal = "I can only help with your own clinic records. I can't access or share another patient's details."
            save_chat(patient_id=patient_id, message=message, response=refusal, db=db)
            return chat_response(refusal)

        if "doctor" in message.casefold() and any(term in message.casefold() for term in (
            "create", "add", "register", "insert", "make a doctor"
        )):
            refusal = "I can't create doctor profiles. I can only search doctors already listed in the clinic database."
            save_chat(patient_id=patient_id, message=message, response=refusal, db=db)
            return chat_response(refusal)


        # =====================================================
        # NORMALIZE
        # =====================================================

        normalized_message = (
            message
            .lower()
            .strip()
            .replace("?", "")
            .replace(".", "")
            .replace("!", "")
        )

        # Handle frequent-headache questions locally. This avoids wasting an
        # LLM call for simple safety guidance and also covers common Hinglish
        # spellings such as "hedach".
        headache_words = ("headache", "headach", "hedache", "hedach", "headch", "sar dard", "sir dard", "sirdard")
        recurring_words = ("baar baar", "bar bar", "barbar", "frequent", "repeated", "again and again", "every day", "roz")
        if any(term in normalized_message for term in headache_words) and any(
            term in normalized_message for term in recurring_words
        ):
            response_text = (
                "Bar-bar headache ke kai reasons ho sakte hain; main diagnosis nahi kar sakta. "
                "Paani piyen, aaram karein, aur note karein ki headache kab hota hai aur kitni der rehta hai. "
                "Agar dard achanak bahut tez ho, head injury ke baad ho, ya saath me weakness, confusion, "
                "vision/speech problem, bukhar ya gardan akadna ho, turant emergency care lein. "
                "Agar yeh baar-baar ho raha hai, clinic doctor se appointment lena sahi rahega."
            )
            save_chat(patient_id=patient_id, message=message, response=response_text, db=db)
            return chat_response(response_text)


        logger.info(
            f"Chat message received. "
            f"patient_id={patient_id}, "
            f"message={message}"
        )


        # =====================================================
        # LOG CURRENT CANCELLATION STATE
        # =====================================================

        logger.info(
            f"CANCEL STATE | "
            f"selection={request.session.get('cancel_selection_pending')} | "
            f"confirmation={request.session.get('cancel_confirmation_pending')} | "
            f"appointment_id={request.session.get('cancel_pending_appointment_id')}"
        )


        # =====================================================
        # 1. USER SAYS NO
        # =====================================================

        if (
            normalized_message in CANCEL_DECLINE_WORDS
            and request.session.get(
                "cancel_confirmation_pending"
            )
        ):

            appointment_id = request.session.get(
                "cancel_pending_appointment_id"
            )

            clear_cancel_session(request)

            response_text = (
                f"Okay. Appointment ID {appointment_id} "
                f"has NOT been cancelled.\n\n"
                f"No refund has been processed."
            )

            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )

            return chat_response(
                response_text
            )


        # =====================================================
        # 2. USER SAYS YES
        # =====================================================

        if (
            normalized_message in {
                "yes",
                "yeah",
                "yep",
                "yup",
                "sure",
                "ok",
                "okay",
                "yes please",
                "sure please",
                "go ahead",
                "please"
            }
            and request.session.get(
                "cancel_confirmation_pending"
            )
        ):

            appointment_id = request.session.get(
                "cancel_pending_appointment_id"
            )


            # -------------------------------------------------
            # NO APPOINTMENT ID IN SESSION
            # -------------------------------------------------

            if not appointment_id:

                clear_cancel_session(request)

                response_text = (
                    "I could not find the appointment "
                    "selected for cancellation.\n\n"
                    "Please start the cancellation again."
                )

                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )

                return chat_response(
                    response_text
                )


            logger.info(
                f"CONFIRMATION RECEIVED | "
                f"patient_id={patient_id} | "
                f"appointment_id={appointment_id}"
            )


            # -------------------------------------------------
            # PROCESS REAL RAZORPAY REFUND
            # -------------------------------------------------

            result = process_refund(
                appointment_id=appointment_id,
                patient_id=patient_id,
                db=db
            )


            # -------------------------------------------------
            # REFUND SUCCESS
            # -------------------------------------------------

            if result.get("success"):

                response_text = (
                    f"✅ Appointment cancelled successfully.\n\n"

                    f"Appointment ID: "
                    f"{appointment_id}\n\n"

                    f"Original payment: "
                    f"₹{float(result['original_amount']):.2f}\n"

                    f"Deduction: "
                    f"{result['deduction_percentage']}%\n"

                    f"Deduction amount: "
                    f"₹{float(result['deduction_amount']):.2f}\n"

                    f"Refund amount: "
                    f"₹{float(result['refund_amount']):.2f}\n"

                    f"Clinic retained: "
                    f"₹{float(result['clinic_retained_amount']):.2f}\n"

                    f"Razorpay Refund ID: "
                    f"{result.get('razorpay_refund_id', 'Processed')}\n\n"

                    f"💳 The refund has been initiated "
                    f"through Razorpay."
                )

                clear_cancel_session(request)


            # -------------------------------------------------
            # REFUND FAILED
            # -------------------------------------------------

            else:

                response_text = (
                    "❌ Appointment was NOT cancelled "
                    "because the Razorpay refund could not "
                    "be processed.\n\n"
                    f"{result.get('message', 'Refund failed.')}"
                )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )

            return chat_response(
                response_text
            )


        # =====================================================
        # 3. DIRECT REFUND REQUEST
        # =====================================================

        if (
            normalized_message in REFUND_WORDS
            and request.session.get(
                "cancel_confirmation_pending"
            )
        ):
            normalized_message = "yes"

            appointment_id = request.session.get(
                "cancel_pending_appointment_id"
            )

            if not appointment_id:

                clear_cancel_session(request)

                response_text = (
                    "I could not find the appointment "
                    "selected for refund.\n\n"
                    "Please start the cancellation again."
                )

                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )

                return chat_response(
                    response_text
                )


            logger.info(
                f"Direct refund request | "
                f"patient_id={patient_id} | "
                f"appointment_id={appointment_id}"
            )


            result = process_refund(
                appointment_id=appointment_id,
                patient_id=patient_id,
                db=db
            )


            if result.get("success"):

                response_text = (
                    f"✅ Appointment cancelled successfully.\n\n"

                    f"Appointment ID: "
                    f"{appointment_id}\n\n"

                    f"Original payment: "
                    f"₹{float(result['original_amount']):.2f}\n"

                    f"Deduction: "
                    f"{result['deduction_percentage']}%\n"

                    f"Deduction amount: "
                    f"₹{float(result['deduction_amount']):.2f}\n"

                    f"Refund amount: "
                    f"₹{float(result['refund_amount']):.2f}\n"

                    f"Clinic retained: "
                    f"₹{float(result['clinic_retained_amount']):.2f}\n"

                    f"Razorpay Refund ID: "
                    f"{result.get('razorpay_refund_id', 'Processed')}\n\n"

                    f"💳 Refund processed through Razorpay."
                )

                clear_cancel_session(request)

            else:

                response_text = (
                    "❌ Razorpay refund was not processed.\n\n"
                    f"{result.get('message', 'Refund failed.')}"
                )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )

            return chat_response(
                response_text
            )


        # =====================================================
        # 4. SHOW MY APPOINTMENTS
        # =====================================================

        if normalized_message in SHOW_APPOINTMENTS_WORDS:

            logger.info(
                f"Show appointments request | "
                f"patient_id={patient_id}"
            )


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


            # -------------------------------------------------
            # NO APPOINTMENTS
            # -------------------------------------------------

            if not appointments:

                response_text = (
                    "You do not have any appointments."
                )

                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )

                return chat_response(
                    response_text
                )


            # -------------------------------------------------
            # BUILD APPOINTMENT LIST
            # -------------------------------------------------

            appointment_lines = []


            for appointment in appointments:

                slot = (
                    db.query(DoctorSlot)
                    .filter(
                        DoctorSlot.id == appointment.slot_id
                    )
                    .first()
                )


                doctor = (
                    db.query(Doctor)
                    .filter(
                        Doctor.id == appointment.doctor_id
                    )
                    .first()
                )


                doctor_name = (
                    doctor.name
                    if doctor
                    else "Unknown doctor"
                )


                specialization = (
                    doctor.specialization
                    if doctor
                    else "Unknown specialization"
                )


                appointment_date = (
                    str(slot.slot_date)
                    if slot
                    else "Unknown date"
                )


                appointment_time = (
                    str(slot.slot_time)
                    if slot
                    else "Unknown time"
                )


                appointment_lines.append(
                    f"🩺 Appointment ID: {appointment.id}\n"
                    f"Doctor: {doctor_name}\n"
                    f"Specialization: {specialization}\n"
                    f"Date: {appointment_date}\n"
                    f"Time: {appointment_time}\n"
                    f"Status: {appointment.status}"
                )


            response_text = (
                "📋 Your appointments:\n\n"
                + "\n\n".join(appointment_lines)
            )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text
            )


        # =====================================================
        # 5. START CANCELLATION
        # =====================================================

        is_cancel_request = (
            normalized_message in CANCEL_WORDS
            or "cancel" in normalized_message
            or "cancal" in normalized_message
            or "cancle" in normalized_message
            or "refund" in normalized_message
        )
        if is_cancel_request:

            logger.info(
                f"Cancellation request received | "
                f"patient_id={patient_id}"
            )


            # -------------------------------------------------
            # GET ACTIVE APPOINTMENTS
            # -------------------------------------------------

            appointments = (
                db.query(Appointment)
                .filter(
                    Appointment.patient_id == patient_id,
                    Appointment.status.in_(
                        ["booked", "checked_in"]
                    )
                )
                .order_by(
                    Appointment.created_at.desc()
                )
                .all()
            )


            if not appointments:

                response_text = (
                    "You do not have any active appointment "
                    "available for cancellation."
                )

                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )

                return chat_response(
                    response_text
                )


            # =================================================
            # ONLY ONE APPOINTMENT
            # =================================================

            if len(appointments) == 1:

                appointment = appointments[0]


                refund_details = calculate_refund(
                    appointment_id=appointment.id,
                    patient_id=patient_id,
                    db=db
                )


                if not refund_details.get("success"):

                    response_text = refund_details.get(
                        "message",
                        "Refund is not available for this appointment."
                    )

                    save_chat(
                        patient_id=patient_id,
                        message=message,
                        response=response_text,
                        db=db
                    )

                    return chat_response(
                        response_text
                    )


                slot = (
                    db.query(DoctorSlot)
                    .filter(
                        DoctorSlot.id == appointment.slot_id
                    )
                    .first()
                )


                doctor = (
                    db.query(Doctor)
                    .filter(
                        Doctor.id == appointment.doctor_id
                    )
                    .first()
                )


                doctor_name = (
                    doctor.name
                    if doctor
                    else "Unknown doctor"
                )


                specialization = (
                    doctor.specialization
                    if doctor
                    else "Unknown specialization"
                )


                appointment_date = (
                    str(slot.slot_date)
                    if slot
                    else "Unknown date"
                )


                appointment_time = (
                    str(slot.slot_time)
                    if slot
                    else "Unknown time"
                )


                # -------------------------------------------------
                # SET ONLY ONE CONFIRMATION STATE
                # -------------------------------------------------

                clear_cancel_session(request)

                request.session[
                    "cancel_pending_appointment_id"
                ] = appointment.id

                request.session[
                    "cancel_confirmation_pending"
                ] = True


                response_text = (
                    f"⚠️ I found your active appointment.\n\n"

                    f"Appointment ID: {appointment.id}\n"
                    f"Doctor: {doctor_name}\n"
                    f"Specialization: {specialization}\n"
                    f"Date: {appointment_date}\n"
                    f"Time: {appointment_time}\n\n"

                    f"Original payment: "
                    f"₹{float(refund_details['original_amount']):.2f}\n"

                    f"Cancellation deduction: "
                    f"{refund_details['deduction_percentage']}%\n"

                    f"Deduction amount: "
                    f"₹{float(refund_details['deduction_amount']):.2f}\n"

                    f"Refund amount: "
                    f"₹{float(refund_details['refund_amount']):.2f}\n\n"

                    f"Do you want to cancel this appointment "
                    f"and process the Razorpay refund?\n\n"

                    f"Please reply Yes or No."
                )


                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )


                return chat_response(
                    response_text
                )


            # =================================================
            # MULTIPLE APPOINTMENTS
            # =================================================

            clear_cancel_session(request)

            request.session[
                "cancel_selection_pending"
            ] = True


            appointment_lines = []


            for appointment in appointments:

                slot = (
                    db.query(DoctorSlot)
                    .filter(
                        DoctorSlot.id == appointment.slot_id
                    )
                    .first()
                )


                doctor = (
                    db.query(Doctor)
                    .filter(
                        Doctor.id == appointment.doctor_id
                    )
                    .first()
                )


                doctor_name = (
                    doctor.name
                    if doctor
                    else "Unknown doctor"
                )


                specialization = (
                    doctor.specialization
                    if doctor
                    else "Unknown specialization"
                )


                appointment_date = (
                    str(slot.slot_date)
                    if slot
                    else "Unknown date"
                )


                appointment_time = (
                    str(slot.slot_time)
                    if slot
                    else "Unknown time"
                )


                appointment_lines.append(
                    f"Appointment ID: {appointment.id}\n"
                    f"Doctor: {doctor_name}\n"
                    f"Specialization: {specialization}\n"
                    f"Date: {appointment_date}\n"
                    f"Time: {appointment_time}\n"
                    f"Status: {appointment.status}"
                )


            response_text = (
                "You have multiple active appointments.\n\n"
                + "\n\n".join(appointment_lines)
                + "\n\n"
                "Please enter the Appointment ID "
                "that you want to cancel."
            )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text
            )


        # =====================================================
        # 6. APPOINTMENT ID FOR CANCELLATION
        # =====================================================

        if (
            normalized_message.isdigit()
            and request.session.get(
                "cancel_selection_pending"
            )
        ):

            appointment_id = int(
                normalized_message
            )


            logger.info(
                f"Cancellation appointment ID received | "
                f"patient_id={patient_id} | "
                f"appointment_id={appointment_id}"
            )


            appointment = (
                db.query(Appointment)
                .filter(
                    Appointment.id == appointment_id,
                    Appointment.patient_id == patient_id,
                    Appointment.status.in_(
                        ["booked", "checked_in"]
                    )
                )
                .first()
            )


            if not appointment:

                response_text = (
                    "I could not find an active appointment "
                    "with that Appointment ID.\n\n"
                    "Please enter a valid Appointment ID."
                )

                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )

                return chat_response(
                    response_text
                )


            # -------------------------------------------------
            # CALCULATE REFUND
            # -------------------------------------------------

            refund_details = calculate_refund(
                appointment_id=appointment_id,
                patient_id=patient_id,
                db=db
            )


            if not refund_details.get("success"):

                clear_cancel_session(request)

                response_text = refund_details.get(
                    "message",
                    "Refund is not available for this appointment."
                )

                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )

                return chat_response(
                    response_text
                )


            # -------------------------------------------------
            # MOVE FROM SELECTION TO CONFIRMATION
            # -------------------------------------------------

            request.session.pop(
                "cancel_selection_pending",
                None
            )

            request.session[
                "cancel_pending_appointment_id"
            ] = appointment_id

            request.session[
                "cancel_confirmation_pending"
            ] = True


            response_text = (
                f"⚠️ Refund preview for Appointment "
                f"{appointment_id}\n\n"

                f"Original payment: "
                f"₹{float(refund_details['original_amount']):.2f}\n"

                f"Cancellation deduction: "
                f"{refund_details['deduction_percentage']}%\n"

                f"Deduction amount: "
                f"₹{float(refund_details['deduction_amount']):.2f}\n"

                f"Refund amount: "
                f"₹{float(refund_details['refund_amount']):.2f}\n\n"

                f"Do you want to cancel this appointment "
                f"and process the Razorpay refund?\n\n"

                f"Please reply Yes or No."
            )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text
            )


        # =====================================================
        # 7. CHECK-IN
        # =====================================================

        if normalized_message in CHECK_IN_WORDS:

            request.session[
                "check_in_pending"
            ] = True


            response_text = (
                "Sure! I can help you check in. "
                "Please enter your appointment ID."
            )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text
            )


        # =====================================================
        # 8. CHECK-IN APPOINTMENT ID
        # =====================================================

        if (
            normalized_message.isdigit()
            and request.session.get(
                "check_in_pending"
            )
        ):

            appointment_id = int(
                normalized_message
            )


            result = check_in_appointment(
                appointment_id=appointment_id,
                patient_id=patient_id,
                db=db
            )


            if result.get("success"):

                request.session.pop(
                    "check_in_pending",
                    None
                )


                response_text = (
                    f"Your appointment ID "
                    f"{appointment_id} has been "
                    f"successfully checked in.\n\n"

                    f"🎫 Your Token Number: "
                    f"{result.get('token_number')}\n\n"

                    f"You can type 'check queue' "
                    f"to see your current queue status."
                )

            else:

                response_text = result.get(
                    "message",
                    "Unable to check in."
                )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text
            )


        # =====================================================
        # 9. CHECK QUEUE STATUS
        # =====================================================

        if normalized_message in CHECK_QUEUE_WORDS:

            logger.info(
                f"Queue status request received | "
                f"patient_id={patient_id}"
            )


            # -------------------------------------------------
            # FIND LATEST CHECKED-IN APPOINTMENT
            # -------------------------------------------------

            appointment = (
                db.query(Appointment)
                .filter(
                    Appointment.patient_id == patient_id,
                    Appointment.status == "checked_in"
                )
                .order_by(
                    Appointment.check_in_time.desc()
                )
                .first()
            )


            # -------------------------------------------------
            # NO CHECKED-IN APPOINTMENT
            # -------------------------------------------------

            if not appointment:

                response_text = (
                    "Please check in first.\n\n"
                    "Type 'check in' to check in "
                    "for your appointment."
                )


                save_chat(
                    patient_id=patient_id,
                    message=message,
                    response=response_text,
                    db=db
                )


                return chat_response(
                    response_text
                )


            # -------------------------------------------------
            # GET QUEUE STATUS
            # -------------------------------------------------

            result = get_queue_status(
                appointment_id=appointment.id,
                patient_id=patient_id,
                db=db
            )


            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if result.get("success"):

                response_text = (
                    f"🎫 Token Number: "
                    f"{result.get('token_number')}\n\n"

                    f"📍 Queue Position: "
                    f"{result.get('queue_position')}\n\n"

                    f"👥 Patients Ahead: "
                    f"{result.get('patients_ahead')}\n\n"

                    f"⏳ Estimated Wait Time: "
                    f"{result.get('estimated_wait_time', 'Calculating...')}"
                )


            # -------------------------------------------------
            # FAILED
            # -------------------------------------------------

            else:

                response_text = result.get(
                    "message",
                    "Unable to fetch queue status."
                )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text
            )


        # =====================================================
        # 10. GENERIC APPOINTMENT REQUEST
        # =====================================================

        doctor_lookup_terms = (
            "doctor", "doctors", "dr.", "available doctor", "find doctor",
            "show doctor", "recommend doctor", "list doctor", "search doctor"
        )

        # Greetings and capability questions need no model call.
        if normalized_message in {
            "hi", "hii", "hello", "hey", "namaste", "good morning",
            "good afternoon", "good evening", "thanks", "thank you",
        }:
            local_response = (
                "Hello! How can I help you today?"
                if normalized_message not in {"thanks", "thank you"}
                else "You're welcome!"
            )
            save_chat(patient_id=patient_id, message=message, response=local_response, db=db)
            return chat_response(local_response)

        if normalized_message in {
            "what can you do", "what can you help with", "help", "how can you help me",
        }:
            local_response = (
                "I can help you check doctors listed by the clinic, view your own appointments "
                "and records, and guide you to a suitable clinic specialty. I can't diagnose."
            )
            save_chat(patient_id=patient_id, message=message, response=local_response, db=db)
            return chat_response(local_response)
        if (
            any(term in normalized_message for term in doctor_lookup_terms)
            and any(term in normalized_message for term in (
                "find", "show", "available", "recommend", "list", "search", "book", "who"
            ))
        ):
            doctors = get_all_available_doctors(db=db)
            response_text = (
                "I couldn't find any available doctors in the clinic database right now. Please contact the clinic for help."
                if not doctors else
                "These are the doctors currently listed as available in the clinic database."
            )
            save_chat(patient_id=patient_id, message=message, response=response_text, db=db)
            return chat_response(
                response_text,
                needs_doctor=bool(doctors),
                needs_appointment=bool(doctors),
                doctors=doctors
            )

        if normalized_message in APPOINTMENT_WORDS:

            doctors = get_all_available_doctors(
                db=db
            )


            response_text = (
                "I couldn't find any available doctors in the clinic database right now. Please contact the clinic for help."
                if not doctors else
                "Here are the doctors currently listed as available. Please select one to view appointment slots."
            )


            request.session.pop(
                "pending_specialization",
                None
            )

            request.session.pop(
                "appointment_specialization",
                None
            )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text,
                needs_doctor=bool(doctors),
                needs_appointment=bool(doctors),
                doctors=doctors
            )


        # =====================================================
        # 11. PENDING SPECIALIZATION
        # =====================================================

        pending_specialization = request.session.get(
            "pending_specialization"
        )


        # =====================================================
        # 12. USER CONFIRMED DOCTOR SEARCH
        # =====================================================

        if (
            normalized_message in CONFIRMATION_WORDS
            and pending_specialization
        ):

            doctors = get_doctors_by_specialization(
                specialization=pending_specialization,
                db=db
            )


            response_text = (
                f"There are no available {pending_specialization} doctors listed in the clinic database right now. Please contact the clinic for help."
                if not doctors else
                f"Here are the {pending_specialization} doctors currently listed as available. Please select one to view appointment slots."
            )


            if doctors:
                request.session["appointment_specialization"] = pending_specialization
            else:
                request.session.pop("appointment_specialization", None)


            request.session.pop(
                "pending_specialization",
                None
            )


            save_chat(
                patient_id=patient_id,
                message=message,
                response=response_text,
                db=db
            )


            return chat_response(
                response_text,
                specialization=pending_specialization if doctors else None,
                needs_doctor=bool(doctors),
                needs_appointment=bool(doctors),
                doctors=doctors
            )


        # =====================================================
        # 13. CHAT HISTORY
        # =====================================================

        conversation_history = get_chat_history(
            patient_id=patient_id,
            db=db,
            limit=2
        )


        # =====================================================
        # 14. LATEST PRESCRIPTION
        # =====================================================

        latest_prescription = request.session.get(
            "latest_prescription"
        )

        # Ground open-ended clinic answers in the patient's own MCP history.
        # Deterministic booking, cancellation and lookup flows above remain intact.
        if (
            request.session.get("role") == "USER"
            and get_query_intent(message) == "llm"
        ):
            try:
                mcp_history = await get_patient_history_context(patient_id)
                conversation_history.append({
                    "role": "system",
                    "content": (
                        "Patient clinical history retrieved through the authenticated "
                        "History MCP tool. Use only if relevant; do not infer missing facts:\n"
                        + mcp_history
                    )
                })
            except Exception as mcp_error:
                logger.warning("MCP history context unavailable: %s", mcp_error)


        if latest_prescription:

            prescription_context = (
                "IMPORTANT PATIENT PRESCRIPTION CONTEXT:\n"
                "The patient has uploaded a prescription.\n"
                "Use the following prescription information "
                "when the patient asks about 'this prescription', "
                "'this medicine', 'my prescription', "
                "'detail about this', etc.\n\n"
                f"{latest_prescription}"
            )


            conversation_history.append(
                {
                    "role": "system",
                    "content": prescription_context
                }
            )


        # =====================================================
        # 15. AI RESPONSE
        # =====================================================

        current_usage = get_usage_status(patient_id)
        if current_usage["used_tokens"] >= USER_DAILY_TOKEN_LIMIT:
            exhausted_response = (
                "Your daily AI message limit has been reached. It will reset tomorrow. "
                "You can still use clinic options that read directly from the database."
            )
            save_chat(patient_id=patient_id, message=message, response=exhausted_response, db=db)
            return {
                **chat_response(exhausted_response),
                "usage_status": current_usage,
                "usage_warning": "EXHAUSTED",
            }

        ai_result = get_chat_response(
            message=message,
            conversation_history=conversation_history,
            user_id=patient_id,
        )


        ai_response = ai_result.get(
            "response",
            "I'm sorry, I could not process your message."
        )


        specialization = ai_result.get(
            "specialization"
        )


        needs_doctor = ai_result.get(
            "needs_doctor",
            False
        )


        needs_confirmation = ai_result.get(
            "needs_confirmation",
            False
        )


        if (
            needs_confirmation
            and specialization
        ):

            request.session[
                "pending_specialization"
            ] = specialization


        doctors = []


        if (
            needs_doctor
            and specialization
        ):

            doctors = get_doctors_by_specialization(
                specialization=specialization,
                db=db
            )

            if not doctors:
                ai_response = (
                    f"There are no available {specialization} doctors listed in the clinic database right now. Please contact the clinic for help."
                )
                needs_doctor = False
                needs_confirmation = False
                request.session.pop("pending_specialization", None)
            elif needs_confirmation:
                ai_response = (
                    f"A {specialization} may be relevant. Would you like me to show the available doctors listed in the clinic database?"
                )


        save_chat(
            patient_id=patient_id,
            message=message,
            response=ai_response,
            db=db
        )


        latest_usage = get_usage_status(patient_id)
        usage_warning = latest_usage["status"] if latest_usage["status"] in {"WARNING", "EXHAUSTED"} else None
        if usage_warning == "WARNING":
            ai_response += "\n\nDaily AI usage is at least 80%; short questions and clinic database options use less AI."
        elif usage_warning == "EXHAUSTED":
            ai_response += "\n\nDaily AI usage limit reached; it resets tomorrow."

        return {
            "success": True,
            "response": ai_response,
            "specialization": specialization,
            "needs_doctor": needs_doctor,
            "needs_confirmation": needs_confirmation,
            "needs_appointment": bool(
                needs_doctor and specialization
            ),
            "doctors": doctors,
            "usage_status": latest_usage,
            "usage_warning": usage_warning,
        }


    except Exception as e:

        logger.exception(
            f"Chatbot error for patient_id="
            f"{request.session.get('patient_id')}: "
            f"{str(e)}"
        )


        return {
            "success": False,
            "message": (
                "Something went wrong while "
                "processing your message."
            )
        }
    finally:
        if chat_slot_acquired:
            _active_chat_patients.discard(patient_id)


# =========================================================
# PATIENT MEDICAL HISTORY
# =========================================================

@router.get("/history")
async def history(
    request: Request,
    db: Session = Depends(get_db)
):

    patient_id = request.session.get(
        "patient_id"
    )

    patient_name = request.session.get(
        "patient_name"
    )


    if not patient_id or request.session.get("role") != "USER":

        return {
            "success": False,
            "message": "Please login first."
        }


    patient_history = get_patient_history(
        patient_id=patient_id,
        db=db
    )


    if not patient_history:

        return {
            "success": True,
            "has_history": False,
            "message":
                f"Hi {patient_name} 👋 "
                f"How can I help you today?"
        }


    return {
        "success": True,
        "has_history": True,
        "patient_name": patient_name,
        "history": patient_history
    }
