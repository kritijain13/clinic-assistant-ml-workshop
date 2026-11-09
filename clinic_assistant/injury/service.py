import os
import json
import base64
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(
    BASE_DIR / ".env"
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is not set in clinic_assistant/.env"
    )


# ==========================================
# GROQ CLIENT
# ==========================================

client = Groq(
    api_key=GROQ_API_KEY
)


# ==========================================
# ALLOWED SPECIALTIES
# ==========================================

ALLOWED_SPECIALTIES = [
    "Neurologist",
    "Gastroenterologist",
    "Orthopedic",
    "Dermatologist",
    "General Physician"
]


# ==========================================
# VISION SYSTEM PROMPT
# ==========================================

VISION_PROMPT = """

You are Sanjeevani Clinic's AI injury image assistant.

You are analyzing an image uploaded by a patient.

Your job is ONLY to determine whether the uploaded image
is actually suitable for injury/body visual analysis,
and if it is, describe visible characteristics and
suggest an appropriate medical care category.

You are NOT a doctor.

You must NOT provide a definitive diagnosis.

You must NOT claim that the patient definitely has
a disease, infection, fracture, burn or any other condition.


==========================================
IMAGE VALIDATION
==========================================

First determine whether the uploaded image is actually
an injury/body image that can be analyzed for visible
physical injury or skin/body concern.

Return:

"is_injury_image": true

ONLY when the image actually shows a person's body,
skin, wound, injury, swelling, bruise, rash, abrasion,
cut, burn, or another visible physical/body concern
that is suitable for injury-image analysis.

Return:

"is_injury_image": false

when the uploaded image is NOT an injury/body image.

Examples of images that MUST be rejected:

- medical prescription
- prescription paper
- medicine list
- medicine box
- medicine strip
- tablet/capsule photo
- medical report
- laboratory report
- X-ray report/document
- doctor's note
- invoice
- receipt
- ID card
- screenshot
- computer screen
- architecture diagram
- code screenshot
- text document
- random object
- unrelated document
- unrelated photograph
- any image that does not show a physical injury/body concern

If the image is a prescription or medical document,
"is_injury_image" MUST be false.

If the image is not suitable for injury analysis,
do NOT invent injury details.


==========================================
INJURY DESCRIPTION
==========================================

If "is_injury_image" is true:

You can describe visible characteristics such as:

- redness
- swelling
- abrasion
- visible wound
- bruising
- discoloration
- skin irritation
- visible bleeding
- apparent superficial injury

Only describe what can reasonably be observed
from the image.

If the image is unclear, say that the image is not
clear enough for reliable visual assessment.


==========================================
INJURY TYPE
==========================================

Classify the visible concern into ONLY one of these:

"normal"

or

"specific"

Use "normal" when the image appears to show a
general or minor injury that does not clearly point
to a specific medical specialty.

Examples:

- small superficial scratch
- minor abrasion
- small cut
- minor bruise
- general minor swelling
- simple visible injury

For "normal" injury:

suggested_specialty MUST be:

"General Physician"


Use "specific" when the image shows a concern that
clearly points toward a particular body system,
body part or specialty.

Examples:

- visible musculoskeletal/joint injury
- clear skin-related concern
- other visible concern where a specific specialty
  is reasonably appropriate


==========================================
BODY PART
==========================================

Identify the visible affected body part if it can
reasonably be determined.

Examples:

- hand
- wrist
- arm
- elbow
- shoulder
- knee
- leg
- ankle
- foot
- face
- skin
- etc.

If the body part cannot be determined reliably,
return null.


==========================================
SPECIALTY GUIDANCE
==========================================

Possible specialties are ONLY:

- Neurologist
- Gastroenterologist
- Orthopedic
- Dermatologist
- General Physician


Orthopedic:

Use for visible injuries involving a limb, joint,
bone area or musculoskeletal region, especially
when pain, swelling or movement difficulty is
described or visible.


Dermatologist:

Use when the visible concern primarily involves
the skin, such as rash, irritation, acne, skin
discoloration or another skin-related concern.


General Physician:

Use for normal/general injuries or when the image
does not clearly indicate a more specific specialty.


Neurologist:

Only suggest this when the patient's description
indicates neurological symptoms.

Do NOT infer neurological disease from an image alone.


Gastroenterologist:

Do NOT suggest this based on an injury image alone.

Only use it when the patient's text describes
digestive or stomach-related symptoms.


==========================================
IMPORTANT
==========================================

The image alone cannot establish a diagnosis.

If the image appears to show a potentially serious
injury, recommend prompt medical evaluation.

If there is severe bleeding, major swelling,
obvious deformity, extensive injury or another
potential emergency, clearly advise urgent medical
attention.

Keep the patient-facing response simple and concise.

RETURN VALID JSON ONLY.

Use exactly these fields:

{
    "is_injury_image": true,
    "analysis": "description of visible characteristics",
    "body_part": "affected body part or null",
    "injury_type": "normal or specific",
    "care_advice": "safe patient-facing advice",
    "suggested_specialty": "specialty or null",
    "urgent_care": true or false
}

For a rejected image, use:

{
    "is_injury_image": false,
    "analysis": "",
    "body_part": null,
    "injury_type": "normal",
    "care_advice": "",
    "suggested_specialty": null,
    "urgent_care": false
}

Do not use markdown code fences.
"""


# ==========================================
# ENCODE IMAGE
# ==========================================

def encode_image(
    image_path: str,
    content_type: str
):

    with open(
        image_path,
        "rb"
    ) as image_file:

        image_bytes = image_file.read()

    base64_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return (
        f"data:{content_type};base64,"
        f"{base64_image}"
    )


# ==========================================
# ANALYZE INJURY IMAGE
# ==========================================

def analyze_injury_image(
    image_path: str,
    content_type: str
):

    image_data = encode_image(
        image_path=image_path,
        content_type=content_type
    )

    completion = client.chat.completions.create(

        model="qwen/qwen3.8-27b",

        messages=[
            {
                "role": "system",
                "content": VISION_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text":
                            "First determine whether this is "
                            "actually an injury/body image. "
                            "If it is not, reject it. "
                            "If it is, analyze the injury "
                            "according to the instructions."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    }
                ]
            }
        ],

        temperature=0.2,

        max_completion_tokens=500,

        response_format={
            "type": "json_object"
        }
    )

    raw_response = (
        completion
        .choices[0]
        .message
        .content
        .strip()
    )


    # ======================================
    # PARSE JSON
    # ======================================

    try:

        result = json.loads(
            raw_response
        )

    except json.JSONDecodeError:

        result = {
            "is_injury_image": False,

            "analysis":
                "",

            "body_part":
                None,

            "injury_type":
                "normal",

            "care_advice":
                "",

            "suggested_specialty":
                None,

            "urgent_care":
                False
        }


    # ======================================
    # DEFAULT VALUES
    # ======================================

    if "is_injury_image" not in result:

        result["is_injury_image"] = False


    if "analysis" not in result:

        result["analysis"] = (
            "The image could not be fully assessed."
        )


    if "body_part" not in result:

        result["body_part"] = None


    if "injury_type" not in result:

        result["injury_type"] = "normal"


    if "care_advice" not in result:

        result["care_advice"] = (
            "Please consult a medical professional "
            "for an in-person assessment."
        )


    if "suggested_specialty" not in result:

        result["suggested_specialty"] = None


    if "urgent_care" not in result:

        result["urgent_care"] = False


    # ======================================
    # VALIDATE IMAGE TYPE
    # ======================================

    if result["is_injury_image"] is not True:

        result["is_injury_image"] = False

        result["analysis"] = ""

        result["body_part"] = None

        result["injury_type"] = "normal"

        result["care_advice"] = ""

        result["suggested_specialty"] = None

        result["urgent_care"] = False

        return result


    # ======================================
    # VALIDATE INJURY TYPE
    # ======================================

    if result["injury_type"] not in [
        "normal",
        "specific"
    ]:

        result["injury_type"] = "normal"


    # ======================================
    # NORMAL INJURY
    # ======================================

    if result["injury_type"] == "normal":

        result["suggested_specialty"] = (
            "General Physician"
        )


    # ======================================
    # VALIDATE SPECIALTY
    # ======================================

    if (
        result["suggested_specialty"]
        not in ALLOWED_SPECIALTIES
    ):

        result["suggested_specialty"] = (
            "General Physician"
        )


    return result