from mcp_layer.auth.auth_service import create_access_token


def generate_token(user_id: int, role: str):

    token = create_access_token(
        user_id,
        role
    )

    return {
        "access_token": token,
        "user_id": user_id,
        "role": role
    }