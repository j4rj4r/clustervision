from pydantic import BaseModel, Field
from typing import Optional
from .user import UserType


class KubeconfigRequest(BaseModel):
    # Same pattern as UserCreate — the username ends up in a Vault path and a
    # Content-Disposition header, so it must stay strictly constrained
    username: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-\.]*$", max_length=253)
    user_type: UserType
    namespace: str = "default"
    # Namespace the ServiceAccount lives in — required to disambiguate SAs
    # sharing a name across namespaces (`namespace` above is only the default
    # context namespace written into the kubeconfig)
    sa_namespace: Optional[str] = Field(None, pattern=r"^[a-z0-9][a-z0-9\-]*$", max_length=63)
    private_key_pem: Optional[str] = None
