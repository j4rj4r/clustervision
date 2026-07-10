from pydantic import BaseModel, Field
from typing import Optional
from .user import UserType


class KubeconfigRequest(BaseModel):
    # Same pattern as UserCreate — the username ends up in a Vault path and a
    # Content-Disposition header, so it must stay strictly constrained
    username: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-\.]*$", max_length=253)
    user_type: UserType
    namespace: str = "default"
    private_key_pem: Optional[str] = None
