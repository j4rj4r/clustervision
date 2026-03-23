from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional


class UserType(str, Enum):
    certificate = "certificate"
    service_account = "service_account"


class UserCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-\.]*$")
    user_type: UserType = UserType.certificate
    groups: list[str] = Field(default_factory=list)
    namespace: str = Field(default="default")


class UserImport(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-\.]*$")
    user_type: UserType
    namespace: str = Field(default="default")
    groups: list[str] = Field(default_factory=list)


class UserRead(BaseModel):
    name: str
    user_type: UserType
    groups: list[str]
    namespace: str
    created_at: str
    cert_expiry: Optional[str] = None
    csr_name: Optional[str] = None


class UserWithCredentials(UserRead):
    private_key_pem: Optional[str] = None
    certificate_pem: Optional[str] = None


class UserList(BaseModel):
    users: list[UserRead]
    total: int
