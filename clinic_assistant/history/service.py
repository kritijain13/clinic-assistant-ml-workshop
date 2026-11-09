from sqlalchemy.orm import Session

from clinic_assistant.database.models import (
    MedicalHistory,
    Doctor,
    ChatHistory
)


# ==========================================
# MEDICAL HISTORY
# ==========================================

def get_patient_history(
    patient_id: int,
    db: Session
):

    history = (
        db.query(
            MedicalHistory,
            Doctor
        )
        .outerjoin(
            Doctor,
            MedicalHistory.doctor_id == Doctor.id
        )
        .filter(
            MedicalHistory.patient_id == patient_id
        )
        .order_by(
            MedicalHistory.visit_date.desc()
        )
        .first()
    )

    if not history:
        return None

    medical_history, doctor = history

    return {
        "problem": medical_history.problem,
        "diagnosis": medical_history.diagnosis,
        "visit_date": medical_history.visit_date,
        "notes": medical_history.notes,
        "doctor_name": (
            doctor.name
            if doctor
            else None
        ),
        "specialization": (
            doctor.specialization
            if doctor
            else None
        )
    }


# ==========================================
# CHAT HISTORY
# ==========================================

def get_chat_history(
    patient_id: int,
    db: Session,
    limit: int = 10
):

    chats = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.patient_id == patient_id
        )
        .order_by(
            ChatHistory.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    chats.reverse()

    conversation = []

    for chat in chats:

        conversation.append(
            {
                "role": "user",
                "content": chat.message
            }
        )

        if chat.response:

            conversation.append(
                {
                    "role": "assistant",
                    "content": chat.response
                }
            )

    return conversation


# ==========================================
# SAVE CHAT
# ==========================================

def save_chat(
    patient_id: int,
    message: str,
    response: str,
    db: Session
):

    chat = ChatHistory(

        patient_id=patient_id,

        message=message,

        response=response

    )

    db.add(chat)

    db.commit()

    db.refresh(chat)

    return chat