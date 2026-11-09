import os

from fastapi import APIRouter, UploadFile, File, Request

from clinic_assistant.prescription.service import (
    process_prescription
)


router = APIRouter(
    prefix="/api/prescription",
    tags=["Prescription"]
)


@router.post("/upload")
async def upload_prescription(
    request: Request,
    file: UploadFile = File(...)
):

    try:

        # ==========================================
        # PATIENT LOGIN CHECK
        # ==========================================

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }


        # ==========================================
        # FILE NAME CHECK
        # ==========================================

        if not file.filename:

            return {
                "success": False,
                "message":
                    "Please select a prescription file."
            }


        # ==========================================
        # ALLOWED FILE TYPES
        # ==========================================

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        }

        file_extension = os.path.splitext(
            file.filename
        )[1].lower()


        if file_extension not in allowed_extensions:

            return {
                "success": False,
                "message":
                    "Please upload JPG, JPEG, PNG "
                    "or WEBP prescription image."
            }


        # ==========================================
        # READ FILE
        # ==========================================

        file_content = await file.read()


        if not file_content:

            return {
                "success": False,
                "message":
                    "Prescription file is empty."
            }


        # ==========================================
        # PROCESS PRESCRIPTION
        # ==========================================

        result = process_prescription(

            file_bytes=file_content,

            original_filename=file.filename,

            patient_id=patient_id

        )


        # ==========================================
        # IF QWEN FAILED
        # ==========================================

        if not result.get("success"):

            return result


        # ==========================================
        # GET PRESCRIPTION DETAILS
        # ==========================================

        prescription_details = result.get(
            "prescription_details",
            {}
        )


        # ==========================================
        # SAVE LATEST PRESCRIPTION IN SESSION
        # ==========================================

        request.session[
            "latest_prescription"
        ] = prescription_details


        # ==========================================
        # RETURN RESULT
        # ==========================================

        return {

            "success": True,

            "message":
                "Prescription uploaded and "
                "analyzed successfully.",

            "filename":
                result.get("filename"),

            "file_path":
                result.get("file_path"),

            "original_filename":
                result.get("original_filename"),

            "prescription_details":
                prescription_details

        }


    except Exception as error:

        return {

            "success": False,

            "message":
                f"Prescription processing failed: "
                f"{str(error)}"

        }
