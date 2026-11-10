from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp_layer.mcp_client.client import process_query
from mcp_layer.token_management.token_budget import get_usage_status
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from mcp_layer.auth.auth_service import get_user_from_token
from mcp_layer.mcp_server.patient_service import get_all_patients
from mcp_layer.mcp_server.doctor_service import get_all_doctors
from mcp_layer.mcp_server.appointment_service import get_all_appointments
from mcp_layer.token_management.token_usage_service import get_today_usage, get_all_users_usage
from mcp_layer.database.initialize import initialize_token_usage_table
app = FastAPI(title="Clinic MCP API")


@app.on_event("startup")
async def initialize_database():
    initialize_token_usage_table()


class ChatRequest(BaseModel):
    query: str
    token: str
    patient_id: int | None = None


def require_user_scope(token: str, requested_user_id: int):
    auth = get_user_from_token(token)
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    if auth["role"] != "SUPER_ADMIN" and auth["user_id"] != requested_user_id:
        raise HTTPException(status_code=403, detail="You can only access your own account data.")
    return auth


@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "Clinic MCP API is running"
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    auth = get_user_from_token(request.token)
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    if auth["role"] not in {"USER", "DOCTOR"}:
        raise HTTPException(status_code=403, detail="Chat access is not allowed for this role.")
    if request.patient_id is not None and request.patient_id != auth["user_id"]:
        raise HTTPException(status_code=403, detail="You can only access your own records.")
    try:
        result = await process_query(request.query, auth["user_id"], auth["role"])
        return {"status": "success", "response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to process the clinic query.") from e
@app.get("/usage/{user_id}")
async def usage(user_id: int, token: str):
    require_user_scope(token, user_id)

    try:
        result = get_today_usage(user_id)

        return {
            "status": "success",
            "usage": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@app.get("/usage-status/{user_id}")
async def usage_status(user_id: int, token: str):
    require_user_scope(token, user_id)
    try:
        result = get_usage_status(user_id)

        return {
            "status": "success",
            "usage": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@app.get(
    "/usage-dashboard/{user_id}",
    response_class=HTMLResponse
)
async def usage_dashboard(user_id: int, token: str):

    require_user_scope(token, user_id)

    return FileResponse(
        "mcp_layer/usage_dashboard.html"
    )
@app.get("/admin/patients")
async def get_admin_patients(token: str):

    auth = get_user_from_token(token)

    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if auth["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required."
        )

    patients = get_all_patients()

    return {
        "status": "success",
        "patients": patients
    }
@app.get("/admin/doctors")
async def get_admin_doctors(token: str):

    auth = get_user_from_token(token)

    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if auth["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required."
        )

    doctors = get_all_doctors()

    return {
        "status": "success",
        "doctors": doctors
    }
@app.get("/admin/appointments")
async def get_admin_appointments(token: str):

    auth = get_user_from_token(token)

    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if auth["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required."
        )

    appointments = get_all_appointments()

    return {
        "status": "success",
        "appointments": appointments
    }
@app.get("/admin/token-usage")
async def admin_token_usage(token: str):

    auth = get_user_from_token(token)

    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if auth["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required."
        )

    usage = get_all_users_usage()

    return {
        "status": "success",
        "usage": usage
    }
@app.get("/admin/token-budget")
async def admin_token_budget(token: str):

    auth = get_user_from_token(token)

    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if auth["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required."
        )

    return {
        "status": "success",
        "daily_limit": 10000,
        "warning_threshold": 80,
        "exhausted_threshold": 100
    }
