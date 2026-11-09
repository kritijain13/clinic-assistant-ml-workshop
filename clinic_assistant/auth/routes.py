import sys
import os
from hmac import compare_digest
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from dotenv import load_dotenv

from clinic_assistant.database.connection import get_db
from clinic_assistant.database.models import Patient
from clinic_assistant.auth.schemas import RegisterRequest, LoginRequest
from clinic_assistant.auth.security import hash_password, verify_password

from src.exception import CustomException
from src.logger import get_logger


logger = get_logger(__name__)

# Load the clinic-local config directly, even when the app is launched from
# another working directory (for example, by Uvicorn's reload process).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/register")
async def register_user(
    user: RegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        existing_user = db.query(Patient).filter(
            Patient.email == user.email
        ).first()

        if existing_user:
            return {
                "success": False,
                "message": "Email already registered"
            }

        hashed_password = hash_password(user.password)

        new_patient = Patient(
            name=user.name,
            email=user.email,
            password=hashed_password,
            phone=user.phone
        )

        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)

        logger.info(f"New patient registered: {user.email}")

        return {
            "success": True,
            "message": "Registration successful",
            "patient_id": new_patient.id
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {str(e)}")
        raise CustomException(e, sys)
@router.post("/login")
async def login_user(
    request: Request,
    user: LoginRequest,
    db: Session = Depends(get_db)
):
    try:

        requested_role = (user.role or "USER").upper()

        # Super User credentials are provisioned outside the public registration flow.
        admin_id = os.getenv("SUPER_ADMIN_ID", "").strip()
        admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "").strip()
        supplied_id = user.email.strip()
        is_super_user_id = bool(
            admin_id and supplied_id.casefold() == admin_id.casefold()
        )
        if requested_role == "SUPER_ADMIN" or is_super_user_id:
            if (admin_id and admin_password
                    and compare_digest(supplied_id.casefold(), admin_id.casefold())
                    and compare_digest(user.password.strip(), admin_password)):
                request.session.clear()
                request.session["patient_id"] = 0
                request.session["patient_name"] = "Super User"
                request.session["role"] = "SUPER_ADMIN"
                return {"success": True, "message": "Login successful",
                        "patient_id": 0, "name": "Super User", "role": "SUPER_ADMIN"}
            if requested_role == "SUPER_ADMIN" and (not admin_id or not admin_password):
                return {"success": False, "message": "Super User credentials are not configured in clinic_assistant/.env"}
            if requested_role == "SUPER_ADMIN":
                return {"success": False, "message": "Invalid ID or password"}

        if requested_role not in {"USER", "DOCTOR"}:
            return {"success": False, "message": "Invalid account type"}

        identity_filters = [Patient.email == user.email]
        if user.email.isdigit():
            identity_filters.append(Patient.id == int(user.email))
        existing_user = db.query(Patient).filter(
            or_(*identity_filters),
            Patient.role == requested_role
        ).first()

        if not existing_user:
            return {
                "success": False,
                "message": "Invalid ID or password"
            }

        password_correct = verify_password(
            user.password,
            existing_user.password
        )

        if not password_correct:
            return {
                "success": False,
                "message": "Invalid ID or password"
            }
        request.session.clear()
        request.session["patient_id"] = existing_user.id
        request.session["patient_name"] = existing_user.name
        request.session["role"] = existing_user.role
        print("LOGIN ROLE:", request.session["role"])

        logger.info(f"Patient login successful: {user.email}")

        return {
        "success": True,
        "message": "Login successful",
        "patient_id": existing_user.id,
        "name": existing_user.name,
        "role": existing_user.role
      }

    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise CustomException(e, sys)
