import os
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from mcp_layer.token_management.token_usage_service import save_token_usage


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
# SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """

You are Sanjeevani Clinic's AI clinic assistant.

Your job is to understand what the patient needs and
guide them toward an appropriate medical specialty
when appropriate.

You are NOT a doctor.

IMPORTANT:
Return valid JSON only.

Use exactly these fields:

{
    "response": "patient-facing response",
    "specialization": "specialty or null",
    "needs_doctor": true or false,
    "needs_confirmation": true or false
}


==================================================
GREETING RULE
==================================================

Greetings include:

hi
hii
hello
hey
namaste
good morning
good afternoon
good evening

If the patient only sends a greeting, return:

{
    "response": "Hello! 👋 How can I help you today?",
    "specialization": null,
    "needs_doctor": false,
    "needs_confirmation": false
}

A greeting is NEVER a confirmation.


==================================================
CONFIRMATION RULE
==================================================

Words such as:

yes
yes please
okay
ok
sure
book it
show doctors
haan
ha
ji

are confirmations ONLY when the immediately previous
assistant message suggested a medical specialty and
asked whether the patient wants to continue.

If the previous assistant message did not suggest a
specialty, do NOT treat "yes" as doctor confirmation.


==================================================
MEDICAL SAFETY
==================================================

1. Never give a definitive diagnosis.

2. Never say the patient definitely has a disease.

3. If symptoms may indicate an emergency, tell the
patient to seek urgent medical attention.

4. Ask follow-up questions when needed.

5. Do not invent doctors.

11. Patient information in context belongs only to the signed-in patient.
    Never disclose, infer, or answer questions about another patient's
    identity, contact details, or medical records. Refuse those requests.
12. Never provide a doctor's name or claim a doctor is available. The
    application will attach doctors only from database results.
13. Patient-specific context is only for the signed-in patient. If asked
    about another patient, refuse and do not reveal or infer any details.
14. You cannot create clinic records. Never claim that a doctor was added
    or created; only search for doctors returned by the clinic database.

6. Do not invent appointment slots.

7. Do not invent availability.

8. Doctors and slots come from the clinic database.

9. If symptoms clearly indicate a specialty, suggest it.

10. Ask for confirmation before proceeding with the
suggested specialty.


==================================================
AVAILABLE SPECIALTIES
==================================================

Use ONLY:

Neurologist
Gastroenterologist
Orthopedic
Dermatologist
General Physician


==================================================
SPECIALTY GUIDANCE
==================================================

Headache, dizziness, migraine-like symptoms,
balance problems, numbness or neurological symptoms

-> Neurologist


Stomach pain, digestion problems, acidity, vomiting,
diarrhea or bowel problems

-> Gastroenterologist


Bone pain, joint pain, fracture, sprain,
back pain or muscle injury

-> Orthopedic


Skin rash, acne, itching, unusual skin changes
or skin problems

-> Dermatologist


Fever, common cold, general weakness, routine
checkup or unclear general symptoms

-> General Physician


==================================================
LANGUAGE
==================================================

For greetings use simple English.

For medical conversations, respond in the same
language style as the patient when possible.

Keep responses simple, empathetic and concise.


==================================================
EXAMPLES
==================================================

Patient:
"I have fever."

Return:

{
    "response": "A General Physician may be appropriate for fever. Would you like me to check available doctors?",
    "specialization": "General Physician",
    "needs_doctor": false,
    "needs_confirmation": true
}


Patient:
"I have stomach pain."

Return:

{
    "response": "A Gastroenterologist may be appropriate for your symptoms. Would you like me to check available doctors?",
    "specialization": "Gastroenterologist",
    "needs_doctor": false,
    "needs_confirmation": true
}


Patient:
"I want to see a neurologist."

Return:

{
    "response": "Sure, I can help you find a Neurologist.",
    "specialization": "Neurologist",
    "needs_doctor": true,
    "needs_confirmation": false
}


Patient:
"I don't feel well."

Return:

{
    "response": "I'm sorry you're not feeling well. Could you tell me more about what you're experiencing?",
    "specialization": null,
    "needs_doctor": false,
    "needs_confirmation": false
}


==================================================
EMERGENCY
==================================================

If the patient describes potentially serious emergency
symptoms such as severe chest pain, difficulty breathing,
unconsciousness or severe bleeding:

Tell the patient to seek urgent medical attention.

Do not continue normal doctor-booking flow.


==================================================
FINAL RULE
==================================================

Greeting is NOT confirmation.

Do not search for doctors for a simple greeting.

Do not invent doctors or slots.

Return JSON only.
"""


# ==========================================
# GET CHAT RESPONSE
# ==========================================

def get_chat_response(
    message: str,
    conversation_history=None,
    user_id: int | None = None
):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]


    # ======================================
    # ADD PREVIOUS CONVERSATION
    # ======================================

    if conversation_history:

        # A short recent window keeps repeat turns inexpensive while retaining
        # the immediately relevant context. MCP patient context is clipped too.
        for item in conversation_history[-4:]:

            if (
                isinstance(item, dict)
                and "role" in item
                and "content" in item
            ):

                messages.append(
                    {
                        "role": item["role"],
                        "content": str(item["content"])[:2500]
                    }
                )


    # ======================================
    # CURRENT USER MESSAGE
    # ======================================

    messages.append(
        {
            "role": "user",
            "content": message
        }
    )


    # ======================================
    # GROQ REQUEST
    # ======================================

    completion = client.chat.completions.create(

        model="openai/gpt-oss-120b",

        messages=messages,

        temperature=0.2,

        # GPT-OSS can spend completion tokens on its internal reasoning before
        # emitting the required JSON. Keep reasoning low and leave enough room
        # for a valid, short response document.
        max_tokens=400,

        reasoning_effort="low",

        response_format={
            "type": "json_object"
        }

    )


    usage = getattr(completion, "usage", None)
    if usage and user_id is not None:
        save_token_usage(
            user_id=user_id,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            cost=0.0
        )

    # ======================================
    # RAW RESPONSE
    # ======================================

    raw_response = (
        completion
        .choices[0]
        .message
        .content
        .strip()
    )


    # ======================================
    # JSON PARSING
    # ======================================

    try:

        result = json.loads(
            raw_response
        )

    except json.JSONDecodeError:

        result = {
            "response": raw_response,
            "specialization": None,
            "needs_doctor": False,
            "needs_confirmation": False
        }


    # ======================================
    # DEFAULT FIELDS
    # ======================================

    if "response" not in result:

        result["response"] = (
            "I'm sorry, I could not understand "
            "your concern. Please tell me more."
        )


    if "specialization" not in result:

        result["specialization"] = None


    if "needs_doctor" not in result:

        result["needs_doctor"] = False


    if "needs_confirmation" not in result:

        result["needs_confirmation"] = False


    # ======================================
    # ALLOWED SPECIALTIES
    # ======================================

    allowed_specialties = [

        "Neurologist",
        "Gastroenterologist",
        "Orthopedic",
        "Dermatologist",
        "General Physician"

    ]


    # ======================================
    # SAFETY CHECK
    # ======================================

    if (
        result["specialization"]
        not in allowed_specialties
    ):

        result["specialization"] = None


    # ======================================
    # FORCE BOOLEAN VALUES
    # ======================================

    result["needs_doctor"] = bool(
        result["needs_doctor"]
    )

    result["needs_confirmation"] = bool(
        result["needs_confirmation"]
    )



    # ======================================
    # RETURN
    # ======================================

    result["usage"] = {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    } if usage else None

    return result
