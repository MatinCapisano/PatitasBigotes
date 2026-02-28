from pydantic import BaseModel, ConfigDict, EmailStr


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class CreateGuestUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
