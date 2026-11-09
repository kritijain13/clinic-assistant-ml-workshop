import os
import sys
import secrets
import uvicorn
from clinic_assistant.injury.routes import router as injury_router
from clinic_assistant.appointments.routes import router as appointment_router
from clinic_assistant.chatbot.routes import router as chatbot_router
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from clinic_assistant.reminder_service import scheduler, send_pending_reminders
from clinic_assistant.reminder_service import scheduler
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from mcp_layer.mcp_client.client import process_query
from src.exception import CustomException
from src.logger import get_logger
from clinic_assistant.prescription.routes import router as prescription_router
from clinic_assistant.payments.routes import router as payment_router
from clinic_assistant.auth.routes import router as auth_router
from clinic_assistant.auth.security import hash_password
from clinic_assistant.database.connection import get_db
from clinic_assistant.database.models import Doctor, Patient
from mcp_layer.mcp_server.patient_service import get_all_patients
from mcp_layer.mcp_server.doctor_service import get_all_doctors
from mcp_layer.mcp_server.appointment_service import get_all_appointments
from mcp_layer.token_management.token_usage_service import get_all_users_usage

logger = get_logger(__name__)

from src.pipeline.predict_pipeline import CustomData, PredictPipeline

from nlp_pretrained.ner_tagger import (get_pos_tags, extract_entities)
from nlp_pretrained.embedding import (most_similar_words)
from nlp_pretrained.sentiment_analyzer import analyze_sentiment


app = FastAPI(title="Covid Prediction Clinic")


# Appointment reminder scheduler
@app.on_event("startup")
async def start_reminder_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("Appointment reminder scheduler started...")

        send_pending_reminders()


app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY") or secrets.token_urlsafe(32)
)


##Set the template folder
templates = Jinja2Templates(directory="templates")

##mouting the css file
app.mount("/static", StaticFiles(directory="static"), name="static")

## Authentication router
app.include_router(auth_router)
app.include_router(chatbot_router)
app.include_router(appointment_router)
app.include_router(injury_router)
app.include_router(payment_router)
app.include_router(prescription_router)


class MCPChatRequest(BaseModel):
    query: str


class DoctorAccountRequest(BaseModel):
    doctor_id: int
    password: str = Field(min_length=10, max_length=128)


@app.post("/api/mcp/chat")
async def mcp_chat(request: Request, payload: MCPChatRequest):
    """Run a signed-in clinic query through MCP tools and the LLM when needed."""
    user_id = request.session.get("patient_id")
    role = request.session.get("role")
    if user_id is None:
        return HTMLResponse(content="Please login first.", status_code=401)
    if role not in {"USER", "DOCTOR"}:
        return HTMLResponse(content="Access denied.", status_code=403)
    query = payload.query.strip()
    if not query:
        return {"success": False, "message": "Please enter a question."}
    return await process_query(query, user_id, role)


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html"
    )


@app.get("/api/auth/session")
async def auth_session(request: Request):
    role = request.session.get("role")
    return {
        "authenticated": role in {"USER", "DOCTOR", "SUPER_ADMIN"},
        "role": role,
        "name": request.session.get("patient_name")
    }


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html"
    )


@app.get("/clinic")
async def clinic_page(request: Request):

    patient_id = request.session.get("patient_id")
    patient_name = request.session.get("patient_name")

    if not patient_id or request.session.get("role") != "USER":
        return RedirectResponse(
            url="/login",
            status_code=302
        )

    return templates.TemplateResponse(
        request,
        "clinic.html",
        {
            "patient_id": patient_id,
            "patient_name": patient_name
        }
    )
@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):

    # Check login
    role = request.session.get("role")

    if role != "SUPER_ADMIN":
        return RedirectResponse(
            url="/login",
            status_code=302
        )

    return templates.TemplateResponse(request, "admin_dashboard.html")


@app.get("/api/admin/dashboard")
async def admin_dashboard_data(request: Request):
    if request.session.get("role") != "SUPER_ADMIN":
        return HTMLResponse(content="Access Denied", status_code=403)
    try:
        patients = get_all_patients()
        doctors = get_all_doctors()
        appointments = get_all_appointments()
        token_usage = get_all_users_usage()

        return {
            "success": True,
            "patients": patients,
            "doctors": doctors,
            "appointments": appointments,
            "token_usage": token_usage
        }

    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        return {
            "success": False,
            "message": "Unable to load dashboard"
        }


@app.post("/api/admin/doctor-accounts")
async def provision_doctor_account(
    request: Request,
    payload: DoctorAccountRequest,
    db: Session = Depends(get_db)
):
    if request.session.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Super User access required.")

    doctor = db.query(Doctor).filter(Doctor.id == payload.doctor_id).first()
    if not doctor or not doctor.email:
        raise HTTPException(status_code=404, detail="Doctor or doctor email not found.")

    account = db.query(Patient).filter(Patient.email == doctor.email).first()
    if account and account.role != "DOCTOR":
        raise HTTPException(
            status_code=409,
            detail="This email belongs to a patient account. Use a different doctor email."
        )

    if account:
        account.name = doctor.name
        account.phone = doctor.phone
        account.password = hash_password(payload.password)
    else:
        account = Patient(
            name=doctor.name,
            email=doctor.email,
            phone=doctor.phone,
            password=hash_password(payload.password),
            role="DOCTOR"
        )
        db.add(account)

    db.commit()
    db.refresh(account)
    return {
        "success": True,
        "message": "Doctor login is ready. Use the doctor's email and chosen password.",
        "account_id": account.id,
        "email": doctor.email
    }


@app.get("/doctor/dashboard")
async def doctor_dashboard(request: Request):
    if not request.session.get("patient_id"):
        return RedirectResponse(url="/login", status_code=302)
    if request.session.get("role") != "DOCTOR":
        return HTMLResponse(content="Access Denied", status_code=403)
    return templates.TemplateResponse(request, "doctor_dashboard.html", {
        "doctor_name": request.session.get("patient_name", "Doctor"),
        "doctor_id": request.session.get("patient_id")
    })


@app.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True}


@app.get("/logout")
async def logout_page(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    logger.info("Home page accessed...")
    return templates.TemplateResponse(
        request,
        "index.html"
    )


@app.get("/predict", response_class=HTMLResponse)
async def predict_form(request: Request):
    logger.info("Predict form page accessed.....")
    return templates.TemplateResponse(
        request,
        "predict.html",
        {"result": None}
    )


@app.post("/predict", response_class=HTMLResponse)
async def predict_result(
    request: Request,
    age: int = Form(...),
    gender: str = Form(...),
    fever: float = Form(...),
    cough: str = Form(...),
    city: str = Form(...)
):
    try:
        logger.info(
            f"Prediction request received :: age{age}, "
            f"gender{gender}, fever{fever}, cough{cough},city{city}"
        )

        custom_data = CustomData(
            age=age,
            gender=gender,
            fever=fever,
            cough=cough,
            city=city
        )

        data_df = custom_data.get_data_as_dataframe()

        predict_pipeline = PredictPipeline()

        result, probability = predict_pipeline.predict(data_df)

        return templates.TemplateResponse(
            request,
            "predict.html",
            {
                "result": result,
                "probability": probability,
                "form_data": {
                    "age": age,
                    "gender": gender,
                    "fever": fever,
                    "cough": cough,
                    "city": city
                }
            }
        )

    except Exception as e:
        raise CustomException(e, sys)


@app.get("/health")
async def health_check():
    logger.info("Monitering alert....")
    return {"status": "ok"}


### NLP Pretrained

@app.get("/pretrained-nlp", response_class=HTMLResponse)
async def pretrained_nlp_form(request: Request):
    return templates.TemplateResponse(
        request,
        "pretrained_nlp.html",
        {
            "result": None,

            "form_data": {
                "query": ""
            },

            "error": None
        }
    )


@app.post("/pretrained-nlp", response_class=HTMLResponse)
async def pretrained_nlp_analysis(
    request: Request,
    query: str = Form(...)
):
    try:

        ## text clean
        query = query.strip()

        if not query:
            return templates.TemplateResponse(
                request,
                "pretrained_nlp.html",
                {
                    "result": None,
                    "form_data": {
                        "query": ""
                    },
                    "error": "Please enter some text..."
                }
            )

        ## Pos tagging
        pos_tags = get_pos_tags(query)

        ## NER
        entities = extract_entities(query)

        ## Sentiment Analysis
        sentiment = analyze_sentiment(query)

        ## Word Embeddings
        similar_words = []

        words = query.split()
        first_word = words[0].lower()

        if words:
            try:
                similar_words = most_similar_words(
                    first_word,
                    topn=5
                )

            except Exception as e:
                logger.warning(
                    f"Glove similarity failed for: ",
                    {first_word},
                    "and the error is:",
                    {e}
                )

                similar_words = []

        ## final result
        result = {
            "query": query,
            "pos_tags": pos_tags,
            "entities": entities,
            "similar_words": similar_words,
            "sentiment": sentiment
        }

        ##render result
        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": result,
                "form_data": {
                    "query": query
                },
                "error": None
            }
        )

    except Exception as e:
        logger.info("Error occured in pretrained nlp analysis")

        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": None,
                "form_data": {
                    "query": query
                },
                "error": str(e)
            }
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
