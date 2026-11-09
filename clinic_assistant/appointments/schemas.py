from pydantic import BaseModel


class AppointmentRequest(BaseModel):

    doctor_id: int
    slot_id: int
    reason: str