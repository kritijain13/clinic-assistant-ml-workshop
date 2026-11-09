import asyncio
from pathlib import Path
from uuid import uuid4
from typing import List

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Request,
    Depends
)

from sqlalchemy.orm import Session

from clinic_assistant.database.connection import get_db
from clinic_assistant.database.models import InjuryImage

from clinic_assistant.injury.service import (
    analyze_injury_image
)

from src.logger import get_logger


logger = get_logger(__name__)


# ==========================================
# ROUTER
# ==========================================

router = APIRouter(
    prefix="/api/injury",
    tags=["Injury"]
)


# ==========================================
# UPLOAD DIRECTORY
# ==========================================

BASE_DIR = Path(
    __file__
).resolve().parents[1]


UPLOAD_DIR = (
    BASE_DIR
    / "uploads"
    / "injuries"
)


UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================
# AI CONCURRENT ANALYSIS LIMIT
# ==========================================

MAX_CONCURRENT_ANALYSIS = 3


# ==========================================
# UPLOAD + ANALYZE MULTIPLE INJURY IMAGES
# ==========================================

@router.post("/upload")
async def upload_injury_images(

    request: Request,

    files: List[UploadFile] = File(...),

    db: Session = Depends(get_db)

):

    try:

        # ==================================
        # CHECK LOGIN
        # ==================================

        patient_id = request.session.get(
            "patient_id"
        )

        if not patient_id or request.session.get("role") != "USER":

            return {
                "success": False,
                "message": "Please login first."
            }


        # ==================================
        # CHECK NUMBER OF FILES
        # ==================================

        if not files:

            return {
                "success": False,
                "message": "Please upload at least one image."
            }


        if len(files) > 10:

            return {
                "success": False,
                "message":
                    "Maximum 10 images can be uploaded at once."
            }


        # ==================================
        # ALLOWED FILE TYPES
        # ==================================

        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp"
        }


        # ==================================
        # MAX FILE SIZE
        # ==================================

        max_size = 10 * 1024 * 1024


        # ==================================
        # RESULT VARIABLES
        # ==================================

        results = {}

        all_specialties = []

        any_urgent = False


        # ==================================
        # PREPARE IMAGES
        # ==================================

        prepared_images = []


        # ==================================
        # READ + SAVE ALL VALID IMAGES
        # ==================================

        for index, file in enumerate(files):

            try:

                # ==================================
                # CHECK FILE TYPE
                # ==================================

                if file.content_type not in allowed_types:

                    results[index] = {

                        "filename":
                            file.filename,

                        "success":
                            False,

                        "message":
                            "Only JPG, PNG and WEBP images are allowed."

                    }

                    continue


                # ==================================
                # READ IMAGE
                # ==================================

                file_content = await file.read()


                # ==================================
                # CHECK FILE SIZE
                # ==================================

                if len(file_content) > max_size:

                    results[index] = {

                        "filename":
                            file.filename,

                        "success":
                            False,

                        "message":
                            "Image size must be less than 10 MB."

                    }

                    continue


                # ==================================
                # CREATE UNIQUE FILE NAME
                # ==================================

                original_name = (
                    file.filename
                    or "injury_image"
                )


                extension = Path(
                    original_name
                ).suffix.lower()


                if not extension:

                    extension = ".jpg"


                unique_name = (
                    f"{uuid4().hex}"
                    f"{extension}"
                )


                file_path = (
                    UPLOAD_DIR
                    / unique_name
                )


                # ==================================
                # SAVE IMAGE
                # ==================================

                with open(
                    file_path,
                    "wb"
                ) as image_file:

                    image_file.write(
                        file_content
                    )


                logger.info(

                    f"Injury image saved "
                    f"for patient_id={patient_id}, "
                    f"filename={file.filename}"

                )


                # ==================================
                # ADD IMAGE TO ANALYSIS QUEUE
                # ==================================

                prepared_images.append({

                    "index":
                        index,

                    "filename":
                        file.filename,

                    "file_path":
                        file_path,

                    "content_type":
                        file.content_type,

                    "unique_name":
                        unique_name

                })


            except Exception as image_error:

                logger.error(

                    f"Error preparing injury image "
                    f"{file.filename}: "
                    f"{str(image_error)}"

                )


                results[index] = {

                    "success":
                        False,

                    "filename":
                        file.filename,

                    "message":
                        "This image could not be processed."

                }


        # ==========================================
        # AI ANALYSIS WITH MAX 3 CONCURRENT REQUESTS
        # ==========================================

        semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_ANALYSIS
        )


        async def analyze_one_image(image_data):

            async with semaphore:

                try:

                    vision_result = await asyncio.to_thread(

                        analyze_injury_image,

                        image_path=str(
                            image_data["file_path"]
                        ),

                        content_type=(
                            image_data["content_type"]
                        )

                    )

                    return {
                        "success":
                            True,

                        "data":
                            image_data,

                        "vision_result":
                            vision_result

                    }


                except Exception as analysis_error:

                    return {

                        "success":
                            False,

                        "data":
                            image_data,

                        "error":
                            analysis_error

                    }


        # ==========================================
        # START AI ANALYSIS
        # ==========================================

        analysis_tasks = [

            analyze_one_image(
                image_data
            )

            for image_data in prepared_images

        ]


        analysis_results = await asyncio.gather(
            *analysis_tasks
        )


        # ==========================================
        # PROCESS AI RESULTS
        # ==========================================

        for analysis_result in analysis_results:

            image_data = analysis_result["data"]

            index = image_data["index"]

            file_path = image_data["file_path"]

            filename = image_data["filename"]

            unique_name = image_data["unique_name"]


            try:

                # ==================================
                # CHECK AI ANALYSIS ERROR
                # ==================================

                if not analysis_result["success"]:

                    try:

                        if file_path.exists():

                            file_path.unlink()

                    except Exception:

                        pass


                    logger.error(

                        f"Error analyzing injury image "
                        f"{filename}: "
                        f"{str(analysis_result.get('error'))}"

                    )


                    results[index] = {

                        "success":
                            False,

                        "filename":
                            filename,

                        "message":
                            "This image could not be analyzed."

                    }

                    continue


                vision_result = (
                    analysis_result["vision_result"]
                )


                # ==================================
                # CHECK WHETHER IMAGE IS ACTUALLY
                # AN INJURY IMAGE
                # ==================================

                if (
                    vision_result.get(
                        "is_injury_image"
                    )
                    is not True
                ):

                    try:

                        if file_path.exists():

                            file_path.unlink()

                    except Exception:

                        pass


                    results[index] = {

                        "success":
                            False,

                        "filename":
                            filename,

                        "message":
                            "This image does not appear to be "
                            "an injury photo. Please upload a "
                            "clear photo of the affected body area."

                    }


                    continue


                # ==================================
                # GET VISION RESULTS
                # ==================================

                analysis = (
                    vision_result.get(
                        "analysis"
                    )
                )


                body_part = (
                    vision_result.get(
                        "body_part"
                    )
                )


                injury_type = (
                    vision_result.get(
                        "injury_type",
                        "normal"
                    )
                )


                care_advice = (
                    vision_result.get(
                        "care_advice"
                    )
                )


                suggested_specialty = (
                    vision_result.get(
                        "suggested_specialty"
                    )
                )


                urgent_care = (
                    vision_result.get(
                        "urgent_care",
                        False
                    )
                )


                # ==================================
                # NORMAL INJURY
                # ==================================

                if injury_type == "normal":

                    suggested_specialty = (
                        "General Physician"
                    )


                # ==================================
                # VALIDATE SPECIALTY
                # ==================================

                allowed_specialties = {

                    "Neurologist",

                    "Gastroenterologist",

                    "Orthopedic",

                    "Dermatologist",

                    "General Physician"

                }


                if (
                    suggested_specialty
                    not in allowed_specialties
                ):

                    suggested_specialty = (
                        "General Physician"
                    )


                # ==================================
                # COLLECT SPECIALTY
                # ==================================

                if suggested_specialty:

                    if (
                        suggested_specialty
                        not in all_specialties
                    ):

                        all_specialties.append(
                            suggested_specialty
                        )


                # ==================================
                # CHECK URGENT CARE
                # ==================================

                if urgent_care:

                    any_urgent = True


                # ==================================
                # SAVE MYSQL RECORD
                # ==================================

                injury_image = InjuryImage(

                    patient_id=patient_id,

                    image_path=(
                        f"uploads/injuries/"
                        f"{unique_name}"
                    ),

                    body_part=body_part,

                    analysis=analysis,

                    suggested_specialty=(
                        suggested_specialty
                    )

                )


                db.add(
                    injury_image
                )


                db.commit()


                db.refresh(
                    injury_image
                )


                # ==================================
                # ADD RESULT
                # ==================================

                results[index] = {

                    "success":
                        True,

                    "filename":
                        filename,

                    "image_id":
                        injury_image.id,

                    "image_path":
                        injury_image.image_path,

                    "analysis":
                        analysis,

                    "body_part":
                        body_part,

                    "injury_type":
                        injury_type,

                    "care_advice":
                        care_advice,

                    "suggested_specialty":
                        suggested_specialty,

                    "urgent_care":
                        urgent_care

                }


                logger.info(

                    f"Injury image analyzed "
                    f"for patient_id={patient_id}, "
                    f"image_id={injury_image.id}, "
                    f"body_part={body_part}, "
                    f"injury_type={injury_type}, "
                    f"specialty={suggested_specialty}"

                )


            except Exception as image_error:

                db.rollback()


                # ==================================
                # DELETE FILE IF PROCESSING FAILED
                # ==================================

                try:

                    if file_path.exists():

                        file_path.unlink()

                except Exception:

                    pass


                logger.error(

                    f"Error processing injury image "
                    f"{filename}: "
                    f"{str(image_error)}"

                )


                results[index] = {

                    "success":
                        False,

                    "filename":
                        filename,

                    "message":
                        "This image could not be analyzed."

                }


        # ==========================================
        # RESTORE ORIGINAL UPLOAD ORDER
        # ==========================================

        results = [

            results[index]

            for index in sorted(
                results.keys()
            )

        ]


        # ==========================================
        # CHECK IF ANY IMAGE SUCCEEDED
        # ==========================================

        successful_results = [

            result

            for result in results

            if result.get("success") is True

        ]


        if not successful_results:

            return {

                "success":
                    False,

                "message":
                    "Unable to analyze the injury photos.",

                "results":
                    results

            }


        # ==========================================
        # SELECT FINAL SPECIALTY
        # ==========================================

        suggested_specialty = None


        if all_specialties:

            # Specific specialty gets priority
            # over General Physician

            specific_specialties = [

                specialty

                for specialty in all_specialties

                if specialty != "General Physician"

            ]


            if specific_specialties:

                suggested_specialty = (
                    specific_specialties[0]
                )

            else:

                suggested_specialty = (
                    "General Physician"
                )


        # ==========================================
        # SAVE SPECIALTY IN SESSION
        # ==========================================

        if suggested_specialty:

            request.session[
                "pending_specialization"
            ] = suggested_specialty


        # ==========================================
        # SAVE BODY PART IN SESSION
        # ==========================================

        body_parts = [

            result.get("body_part")

            for result in successful_results

            if result.get("body_part")

        ]


        if body_parts:

            request.session[
                "pending_body_part"
            ] = ", ".join(

                dict.fromkeys(
                    body_parts
                )

            )


        # ==========================================
        # SAVE INJURY TYPE IN SESSION
        # ==========================================

        injury_types = [

            result.get("injury_type")

            for result in successful_results

            if result.get("injury_type")

        ]


        if injury_types:

            if "specific" in injury_types:

                request.session[
                    "pending_injury_type"
                ] = "specific"

            else:

                request.session[
                    "pending_injury_type"
                ] = "normal"


        # ==========================================
        # COMBINE CARE ADVICE
        # ==========================================

        care_advice_list = [

            result.get("care_advice")

            for result in successful_results

            if result.get("care_advice")

        ]


        combined_care_advice = "\n\n".join(

            dict.fromkeys(
                care_advice_list
            )

        )


        # ==========================================
        # FINAL RESPONSE
        # ==========================================

        return {

            "success":
                True,

            "message":
                "Injury photos uploaded and analyzed successfully.",

            "results":
                successful_results,

            "care_advice":
                combined_care_advice,

            "suggested_specialty":
                suggested_specialty,

            "body_parts":
                list(
                    dict.fromkeys(
                        body_parts
                    )
                ),

            "injury_type":
                request.session.get(
                    "pending_injury_type"
                ),

            "urgent_care":
                any_urgent

        }


    except Exception as e:

        db.rollback()


        logger.error(

            f"Injury upload error: "
            f"{str(e)}"

        )


        return {

            "success":
                False,

            "message":
                "Something went wrong while processing the injury photos."

        }
