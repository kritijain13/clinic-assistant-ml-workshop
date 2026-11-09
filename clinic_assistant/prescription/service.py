import os
import json
import uuid
import time

from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from google import genai
from google.genai import types

from clinic_assistant.database.connection import SessionLocal
from clinic_assistant.database.models import Prescription


# =========================================================
# PATH
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_PATH = os.path.join(
    BASE_DIR,
    ".env"
)

load_dotenv(
    ENV_PATH,
    override=True
)


# =========================================================
# GEMINI CONFIG
# =========================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

# Number of Gemini attempts
MAX_GEMINI_RETRIES = 3

# Wait times between attempts
RETRY_DELAYS = [2, 4, 8]


# =========================================================
# PRESCRIPTION DIRECTORY
# =========================================================

PRESCRIPTION_DIR = os.path.join(
    BASE_DIR,
    "uploads",
    "prescriptions"
)

os.makedirs(
    PRESCRIPTION_DIR,
    exist_ok=True
)


# =========================================================
# ALLOWED FILES
# =========================================================

ALLOWED_IMAGE_TYPES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

MAX_FILE_SIZE = 10 * 1024 * 1024


# =========================================================
# SAVE PRESCRIPTION FILE
# =========================================================

def save_prescription_file(
    file_bytes: bytes,
    original_filename: str,
    patient_id: int
):

    extension = os.path.splitext(
        original_filename
    )[1].lower()

    if not extension:
        extension = ".jpg"

    unique_name = (
        f"patient_{patient_id}_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = os.path.join(
        PRESCRIPTION_DIR,
        unique_name
    )

    with open(
        file_path,
        "wb"
    ) as file:

        file.write(
            file_bytes
        )

    return unique_name, file_path


# =========================================================
# GEMINI PRESCRIPTION ANALYSIS
# =========================================================

def analyze_prescription(
    file_path: str
):

    if not GEMINI_API_KEY:

        return {
            "success": False,
            "message": (
                "GEMINI_API_KEY is missing "
                "in clinic_assistant/.env"
            )
        }

    # -----------------------------------------------------
    # READ IMAGE
    # -----------------------------------------------------

    try:

        with open(
            file_path,
            "rb"
        ) as file:

            image_bytes = file.read()

    except Exception as error:

        return {
            "success": False,
            "message": (
                f"Unable to read prescription image: "
                f"{str(error)}"
            )
        }

    # -----------------------------------------------------
    # MIME TYPE
    # -----------------------------------------------------

    extension = os.path.splitext(
        file_path
    )[1].lower()

    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }.get(
        extension,
        "image/jpeg"
    )

    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = """
You are a prescription-reading assistant.

Read the uploaded image carefully.

First determine whether the uploaded image is actually
a medical prescription.

Extract ONLY information that is visibly present
in the prescription.

DO NOT invent or guess information.

DO NOT diagnose the patient yourself.

DO NOT recommend new medicines.

Return ONLY valid JSON.

Use exactly this structure:

{
    "is_prescription": true,
    "doctor_name": "",
    "patient_name": "",
    "prescription_date": "",
    "medicines": [
        {
            "name": "",
            "strength": "",
            "dosage": "",
            "frequency": "",
            "duration": "",
            "timing": "",
            "instructions": ""
        }
    ],
    "diagnosis": "",
    "instructions": "",
    "follow_up": ""
}

Rules:

1. Read medicine names carefully.
2. Extract strength if visible.
3. Extract dosage if visible.
4. Extract frequency if visible.
5. Extract duration if visible.
6. Extract before/after food information if visible.
7. Extract doctor name if visible.
8. Extract patient name if visible.
9. Extract prescription date if visible.
10. Extract diagnosis only if clearly written.
11. Extract doctor's instructions if visible.
12. If information is not visible, return an empty string.
13. Never guess unclear handwriting.
14. Never create a medicine that is not visible.
15. First decide whether the uploaded image is actually a medical prescription.
16. If the image is NOT a prescription, set "is_prescription" to false.
17. If the image is NOT a prescription, do not extract or invent prescription details.
"""


    # -----------------------------------------------------
    # GEMINI CLIENT
    # -----------------------------------------------------

    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception as error:

        return {
            "success": False,
            "message":
                f"Unable to initialize Gemini client: {str(error)}"
        }


    # =====================================================
    # GEMINI RETRY LOOP
    # =====================================================

    last_error = None

    for attempt in range(
        MAX_GEMINI_RETRIES
    ):

        try:

            print(
                f"Gemini prescription analysis "
                f"attempt {attempt + 1}/"
                f"{MAX_GEMINI_RETRIES}"
            )

            response = client.models.generate_content(

                model=GEMINI_MODEL,

                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    ),
                    prompt
                ],

                config=types.GenerateContentConfig(
                    temperature=0
                )
            )


            # -------------------------------------------------
            # GET RESPONSE
            # -------------------------------------------------

            text = response.text

            if not text:

                return {
                    "success": False,
                    "message":
                        "Gemini returned an empty response."
                }

            text = text.strip()


            # -------------------------------------------------
            # REMOVE MARKDOWN JSON
            # -------------------------------------------------

            if text.startswith("```json"):

                text = text[7:]

            elif text.startswith("```"):

                text = text[3:]


            if text.endswith("```"):

                text = text[:-3]


            text = text.strip()


            # -------------------------------------------------
            # JSON PARSE
            # -------------------------------------------------

            try:

                prescription_details = json.loads(
                    text
                )

            except json.JSONDecodeError:

                return {
                    "success": False,
                    "message":
                        "Prescription was read, but "
                        "Gemini returned invalid JSON.",
                    "raw_response":
                        text
                }


            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            return {
                "success": True,
                "prescription_details":
                    prescription_details
            }


        except Exception as error:

            last_error = error

            error_text = str(error)

            print(
                f"Gemini attempt {attempt + 1} failed: "
                f"{error_text}"
            )


            # -------------------------------------------------
            # CHECK WHETHER IT IS A 503 ERROR
            # -------------------------------------------------

            is_503 = (
                "503" in error_text
                or
                "UNAVAILABLE" in error_text
                or
                "high demand" in error_text.lower()
            )


            # -------------------------------------------------
            # RETRY ONLY TEMPORARY AVAILABILITY ERRORS
            # -------------------------------------------------

            if (
                is_503
                and
                attempt < MAX_GEMINI_RETRIES - 1
            ):

                delay = RETRY_DELAYS[attempt]

                print(
                    f"Gemini temporarily unavailable. "
                    f"Retrying in {delay} seconds..."
                )

                time.sleep(
                    delay
                )

                continue


            # -------------------------------------------------
            # OTHER ERRORS
            # -------------------------------------------------

            break


    # =====================================================
    # ALL ATTEMPTS FAILED
    # =====================================================

    return {
        "success": False,
        "message": (
            "Gemini prescription analysis is temporarily "
            "unavailable. Please try uploading the "
            "prescription again after a short while."
        ),
        "error": str(last_error)
    }


# =========================================================
# SAVE PRESCRIPTION DETAILS TO MYSQL
# =========================================================

def save_prescription_to_db(
    patient_id: int,
    original_filename: str,
    saved_filename: str,
    file_path: str,
    prescription_details: dict
):

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # GET DATA FROM GEMINI RESULT
        # -------------------------------------------------

        doctor_name = prescription_details.get(
            "doctor_name",
            ""
        )

        patient_name = prescription_details.get(
            "patient_name",
            ""
        )

        prescription_date = prescription_details.get(
            "prescription_date",
            ""
        )

        diagnosis = prescription_details.get(
            "diagnosis",
            ""
        )

        instructions = prescription_details.get(
            "instructions",
            ""
        )

        follow_up = prescription_details.get(
            "follow_up",
            ""
        )

        medicines = prescription_details.get(
            "medicines",
            []
        )


        # -------------------------------------------------
        # CONVERT MEDICINES TO JSON STRING
        # -------------------------------------------------

        medicines_json = json.dumps(
            medicines,
            ensure_ascii=False
        )


        # -------------------------------------------------
        # CREATE DATABASE OBJECT
        # -------------------------------------------------

        prescription = Prescription(

            patient_id=patient_id,

            original_filename=original_filename,

            saved_filename=saved_filename,

            file_path=file_path,

            doctor_name=doctor_name,

            patient_name=patient_name,

            prescription_date=prescription_date,

            diagnosis=diagnosis,

            instructions=instructions,

            follow_up=follow_up,

            medicines=medicines_json
        )


        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        db.add(
            prescription
        )

        db.commit()

        db.refresh(
            prescription
        )


        return {
            "success": True,
            "prescription_id":
                prescription.id
        }


    except Exception as error:

        db.rollback()

        return {
            "success": False,
            "message":
                f"Failed to save prescription to MySQL: {str(error)}"
        }


    finally:

        db.close()


# =========================================================
# MAIN SERVICE FUNCTION
# =========================================================

def process_prescription(
    file_bytes: bytes,
    original_filename: str,
    patient_id: int
):

    # -----------------------------------------------------
    # VALIDATE FILE
    # -----------------------------------------------------

    if not file_bytes:

        return {
            "success": False,
            "message":
                "Prescription file is empty."
        }


    if len(file_bytes) > MAX_FILE_SIZE:

        return {
            "success": False,
            "message":
                "Prescription file must be smaller than 10 MB."
        }


    extension = os.path.splitext(
        original_filename
    )[1].lower()


    if extension not in ALLOWED_IMAGE_TYPES:

        return {
            "success": False,
            "message":
                "Please upload JPG, JPEG, PNG or WEBP prescription."
        }


    # -----------------------------------------------------
    # CHECK WHETHER FILE IS A REAL IMAGE
    # -----------------------------------------------------

    try:

        image = Image.open(
            BytesIO(file_bytes)
        )

        image.verify()

    except Exception:

        return {
            "success": False,
            "message": (
                "The uploaded file is not a valid image. "
                "Please upload a valid JPG, JPEG, PNG or WEBP image."
            )
        }


    # -----------------------------------------------------
    # SAVE FILE
    # -----------------------------------------------------

    saved_filename, file_path = (
        save_prescription_file(
            file_bytes=file_bytes,
            original_filename=original_filename,
            patient_id=patient_id
        )
    )


    # -----------------------------------------------------
    # ANALYZE WITH GEMINI
    # -----------------------------------------------------

    analysis = analyze_prescription(
        file_path
    )


    # -----------------------------------------------------
    # ANALYSIS FAILED
    # -----------------------------------------------------

    if not analysis.get("success"):

        try:

            if os.path.exists(file_path):

                os.remove(file_path)

        except Exception:

            pass


        return {
            "success": False,
            "message":
                analysis.get(
                    "message",
                    "Prescription analysis failed."
                ),
            "filename":
                saved_filename,
            "file_path":
                file_path,
            "original_filename":
                original_filename
        }


    # -----------------------------------------------------
    # GET PRESCRIPTION DETAILS
    # -----------------------------------------------------

    prescription_details = analysis.get(
        "prescription_details",
        {}
    )


    # -----------------------------------------------------
    # CHECK WHETHER FILE IS ACTUALLY A PRESCRIPTION
    # -----------------------------------------------------

    if prescription_details.get(
        "is_prescription"
    ) is not True:

        try:

            if os.path.exists(file_path):

                os.remove(file_path)

        except Exception:

            pass


        return {
            "success": False,
            "message": (
                "This image does not appear to be a "
                "prescription. Please upload a valid "
                "prescription."
            ),
            "original_filename":
                original_filename
        }


    # -----------------------------------------------------
    # SAVE TO MYSQL
    # -----------------------------------------------------

    db_result = save_prescription_to_db(

        patient_id=patient_id,

        original_filename=original_filename,

        saved_filename=saved_filename,

        file_path=file_path,

        prescription_details=prescription_details
    )


    # -----------------------------------------------------
    # DATABASE SAVE FAILED
    # -----------------------------------------------------

    if not db_result.get("success"):

        return {

            "success": False,

            "message":
                db_result.get(
                    "message",
                    "Prescription analyzed but "
                    "could not be saved to MySQL."
                ),

            "filename":
                saved_filename,

            "file_path":
                file_path,

            "original_filename":
                original_filename,

            "prescription_details":
                prescription_details
        }


    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    return {

        "success": True,

        "message":
            "Prescription uploaded, analyzed "
            "and saved successfully.",

        "prescription_id":
            db_result.get(
                "prescription_id"
            ),

        "filename":
            saved_filename,

        "file_path":
            file_path,

        "original_filename":
            original_filename,

        "prescription_details":
            prescription_details
    }