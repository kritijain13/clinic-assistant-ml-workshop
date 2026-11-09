ROLE_PERMISSIONS = {

    "USER": [
        "appointment:read",
        "appointment:book",
        "history:read",
        "doctor:read",
    ],

    "DOCTOR": [
        "doctor:read",
    ],

    "ADMIN": [
        "appointment:read",
        "appointment:book",
        "appointment:manage",
        "patient:read",
        "refund:manage",
        "audit:read",
    ],

    "SYSTEM": [
        "reminder:send",
        "email:send",
    ],

    "SUPER_ADMIN": [
        "*"
    ]
}


def has_permission(role: str, permission: str) -> bool:

    permissions = ROLE_PERMISSIONS.get(role, [])

    if "*" in permissions:
        return True

    return permission in permissions
