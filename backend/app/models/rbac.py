from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class PolicyRule(BaseModel):
    api_groups: list[str] = Field(default_factory=lambda: [""])
    resources: list[str]
    verbs: list[str]
    resource_names: Optional[list[str]] = None


class RoleCreate(BaseModel):
    name: str
    namespace: str
    rules: list[PolicyRule]


class ClusterRoleCreate(BaseModel):
    name: str
    rules: list[PolicyRule]


class RoleUpdate(BaseModel):
    rules: list[PolicyRule]


class RoleRead(BaseModel):
    name: str
    namespace: Optional[str] = None
    rules: list[PolicyRule]
    is_system: bool = False


class SubjectKind(str, Enum):
    User = "User"
    Group = "Group"
    ServiceAccount = "ServiceAccount"


class Subject(BaseModel):
    kind: SubjectKind
    name: str
    namespace: Optional[str] = None


class BindingCreate(BaseModel):
    name: str
    role_name: str
    role_kind: str = Field(..., pattern=r"^(ClusterRole|Role)$")
    subjects: list[Subject]
    namespace: Optional[str] = None


class BindingRead(BaseModel):
    name: str
    namespace: Optional[str]
    role_ref: str
    role_kind: str
    subjects: list[Subject]


class AssignRoleRequest(BaseModel):
    role_name: str
    role_kind: str = Field(default="ClusterRole", pattern=r"^(ClusterRole|Role)$")
    namespace: Optional[str] = None


class UserPermissionSummary(BaseModel):
    username: str
    cluster_bindings: list[BindingRead]
    namespace_bindings: list[BindingRead]


class NamespaceAccessEntry(BaseModel):
    subject: str
    subject_kind: str
    subject_namespace: Optional[str] = None
    role: str
    role_kind: str
    binding: str
    scope: str  # 'namespace' | 'cluster'


class CheckAccessRequest(BaseModel):
    user: str
    verb: str
    resource: str
    namespace: Optional[str] = None
    api_group: str = ""


class CheckAccessResult(BaseModel):
    allowed: bool
    denied: bool
    reason: str
