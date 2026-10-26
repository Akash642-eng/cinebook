import re
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)

    password: str = Field(min_length=12, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = re.sub(r"[\s().-]", "", value).strip()
        if not re.fullmatch(r"\+?[0-9]{7,15}", normalized):
            raise ValueError("Enter a valid phone number with 7–15 digits.")
        return normalized


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
