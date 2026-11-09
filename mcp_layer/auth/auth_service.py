import jwt
import os
import secrets
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("MCP_SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("RENDER", "").lower() == "true" or os.getenv("ENVIRONMENT", "").lower() == "production":
        raise RuntimeError(
            "MCP_SECRET_KEY must be configured in production to sign and validate MCP tokens."
        )
    # A process-local key is sufficient for local development and is never a production fallback.
    SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"


def create_access_token(user_id: int, role: str):

    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def get_user_from_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return {
            "user_id": payload["user_id"],
            "role": payload["role"]
        }

    except jwt.PyJWTError:

        return None
