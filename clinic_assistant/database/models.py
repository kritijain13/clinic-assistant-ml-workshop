from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Time,
    Float,
    ForeignKey,
    Boolean
)

from clinic_assistant.database.connection import Base


class Patient(Base):

    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(String(20), nullable=False, default="USER")
    created_at = Column(DateTime, default=datetime.utcnow)



class Doctor(Base):

    __tablename__ = "doctors"

    consultation_fee = Column(Float, nullable=False, default=500.00)

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    specialization = Column(String(100), nullable=False)

    location = Column(
        String(100),
        nullable=False,
        default="Jaipur"
    )

    experience_years = Column(Integer)

    phone = Column(String(20))

    email = Column(String(150))

    available = Column(Boolean, default=True)


class DoctorSlot(Base):

    __tablename__ = "doctor_slots"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_date = Column(Date, nullable=False)
    slot_time = Column(Time, nullable=False)
    is_booked = Column(Boolean, default=False)


class Appointment(Base):

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("doctor_slots.id"), nullable=False)
    reason = Column(Text)
    status = Column(String(50), default="booked")
    reminder_sent = Column(Boolean, default=False)

    # Queue fields
    token_number = Column(Integer, nullable=True)
    check_in_time = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class MedicalHistory(Base):

    __tablename__ = "medical_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    problem = Column(Text)
    diagnosis = Column(Text)
    visit_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)


class InjuryImage(Base):

    __tablename__ = "injury_images"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    body_part = Column(String(100))
    analysis = Column(Text)
    suggested_specialty = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatHistory(Base):

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Payment(Base):

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False
    )

    amount = Column(Float, nullable=False)

    payment_status = Column(
        String(50),
        default="pending"
    )

    transaction_id = Column(
        String(100),
        unique=True,
        nullable=True
    )

    # Razorpay fields
    razorpay_order_id = Column(
        String(100),
        nullable=True
    )

    razorpay_payment_id = Column(
        String(100),
        nullable=True
    )

    razorpay_signature = Column(
        String(255),
        nullable=True
    )

    # -----------------------------------------
    # REFUND FIELDS
    # -----------------------------------------

    deduction_percentage = Column(
        Float,
        nullable=True
    )

    deduction_amount = Column(
        Float,
        nullable=True
    )

    refund_amount = Column(
        Float,
        nullable=True
    )

    clinic_retained_amount = Column(
        Float,
        nullable=True
    )

    razorpay_refund_id = Column(
        String(100),
        nullable=True
    )

    refund_date = Column(
        DateTime,
        nullable=True
    )

    # -----------------------------------------
    # PAYMENT DATE
    # -----------------------------------------

    payment_date = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class PaymentReceipt(Base):

    __tablename__ = "payment_receipts"

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(
        Integer,
        ForeignKey("payments.id"),
        nullable=False
    )

    receipt_number = Column(
        String(100),
        unique=True,
        nullable=False
    )

    receipt_path = Column(
        String(500),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Prescription(Base):

    __tablename__ = "prescriptions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False
    )

    original_filename = Column(
        String(255),
        nullable=True
    )

    saved_filename = Column(
        String(255),
        nullable=True
    )

    file_path = Column(
        String(500),
        nullable=True
    )

    doctor_name = Column(
        String(255),
        nullable=True
    )

    patient_name = Column(
        String(255),
        nullable=True
    )

    prescription_date = Column(
        String(100),
        nullable=True
    )

    diagnosis = Column(
        Text,
        nullable=True
    )

    instructions = Column(
        Text,
        nullable=True
    )

    follow_up = Column(
        Text,
        nullable=True
    )

    medicines = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class DiseaseGroup(Base):

    __tablename__ = "disease_groups"

    cluster_id = Column(Integer, primary_key=True)
    disease_group = Column(String(255), nullable=False)
    patient_ids = Column(Text, nullable=False)
class AppointmentReminder(Base):
    __tablename__ = "appointment_reminders"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False,
        unique=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False
    )

    reminder_type = Column(
        String(50),
        default="24_hours"
    )

    sent_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )