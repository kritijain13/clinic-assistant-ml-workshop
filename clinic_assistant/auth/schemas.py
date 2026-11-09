from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str = "USER"
