from mcp_layer.auth.auth_service import get_user_from_token
from mcp_layer.security.rbac import has_permission


def authorize(token: str, required_permission: str):

    user = get_user_from_token(token)

    if not user:
        return {
            "allowed": False,
            "message": "Invalid or expired token."
        }

    role = user["role"]

    allowed = has_permission(
        role,
        required_permission
    )

    if not allowed:
        return {
            "allowed": False,
            "user_id": user["user_id"],
            "role": role,
            "message": "Permission denied."
        }

    return {
        "allowed": True,
        "user_id": user["user_id"],
        "role": role
    }