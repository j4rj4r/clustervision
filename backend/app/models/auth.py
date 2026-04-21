from pydantic import BaseModel
from typing import Literal


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["admin", "viewer"]
    username: str


class UserInfo(BaseModel):
    username: str
    role: Literal["admin", "viewer"]
