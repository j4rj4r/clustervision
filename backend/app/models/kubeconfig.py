from pydantic import BaseModel
from typing import Optional
from .user import UserType


class KubeconfigRequest(BaseModel):
    username: str
    user_type: UserType
    namespace: str = "default"
    private_key_pem: Optional[str] = None
