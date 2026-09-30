from typing import Literal

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


RoleName = Literal["viewer", "operator", "approver", "admin"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    roles: dict[str, RoleName]
    username: str


class UserInfo(BaseModel):
    username: str
    roles: dict[str, RoleName]


class LinkedUserRead(BaseModel):
    name: str
    namespace: str


class LinkedUserSet(BaseModel):
    name: str
    namespace: str = "default"
