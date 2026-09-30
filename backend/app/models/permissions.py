from pydantic import BaseModel

from .auth import RoleName


class ScopeRoleRead(BaseModel):
    scope: str
    role: RoleName


class ScopeRoleSet(BaseModel):
    role: RoleName
