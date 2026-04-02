import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..models.rbac import PolicyRule, Subject, SubjectKind

logger = logging.getLogger(__name__)


def _rule_to_k8s(rule: PolicyRule) -> client.V1PolicyRule:
    return client.V1PolicyRule(
        api_groups=rule.api_groups,
        resources=rule.resources,
        verbs=rule.verbs,
        resource_names=rule.resource_names,
    )


def _rule_from_k8s(rule: client.V1PolicyRule) -> dict:
    return {
        "api_groups": rule.api_groups or [""],
        "resources": rule.resources or [],
        "verbs": rule.verbs or [],
        "resource_names": rule.resource_names,
    }


def _subject_to_k8s(s: Subject) -> client.RbacV1Subject:
    return client.RbacV1Subject(
        kind=s.kind.value,
        name=s.name,
        namespace=s.namespace,
    )


def _subject_from_k8s(s: client.RbacV1Subject) -> dict:
    return {"kind": s.kind, "name": s.name, "namespace": s.namespace}


class RbacService:
    def __init__(self, api_client: client.ApiClient):
        self.rbac_v1 = client.RbacAuthorizationV1Api(api_client)
        self.core_v1 = client.CoreV1Api(api_client)
        self.auth_v1 = client.AuthorizationV1Api(api_client)

    # ── ClusterRoles ────────────────────────────────────────────────────────

    def list_cluster_roles(
        self,
        include_system: bool = False,
        limit: int = 500,
        _continue: Optional[str] = None,
    ) -> dict:
        kwargs: dict = {"limit": limit}
        if _continue:
            kwargs["_continue"] = _continue
        result = self.rbac_v1.list_cluster_role(**kwargs)
        items = []
        for r in result.items:
            is_system = r.metadata.name.startswith("system:") or r.metadata.name.startswith("kubeadm:")
            if not include_system and is_system:
                continue
            items.append({
                "name": r.metadata.name,
                "rules": [_rule_from_k8s(rule) for rule in (r.rules or [])],
                "is_system": is_system,
            })
        return {
            "items": items,
            "total": len(items),
            "next_continue": result.metadata._continue,
        }

    def get_cluster_role(self, name: str) -> dict:
        r = self.rbac_v1.read_cluster_role(name)
        return {
            "name": r.metadata.name,
            "rules": [_rule_from_k8s(rule) for rule in (r.rules or [])],
            "is_system": r.metadata.name.startswith("system:"),
        }

    def create_cluster_role(self, name: str, rules: list[PolicyRule]) -> dict:
        cr = client.V1ClusterRole(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={"managed-by": "clustervision"},
            ),
            rules=[_rule_to_k8s(r) for r in rules],
        )
        created = self.rbac_v1.create_cluster_role(cr)
        return {"name": created.metadata.name}

    def update_cluster_role(self, name: str, rules: list[PolicyRule]) -> dict:
        cr = self.rbac_v1.read_cluster_role(name)
        cr.rules = [_rule_to_k8s(r) for r in rules]
        updated = self.rbac_v1.replace_cluster_role(name, cr)
        return {
            "name": updated.metadata.name,
            "rules": [_rule_from_k8s(r) for r in (updated.rules or [])],
            "is_system": updated.metadata.name.startswith("system:"),
        }

    def delete_cluster_role(self, name: str):
        self.rbac_v1.delete_cluster_role(name)

    # ── Namespaced Roles ────────────────────────────────────────────────────

    def list_roles(
        self,
        namespace: str,
        limit: int = 500,
        _continue: Optional[str] = None,
    ) -> dict:
        kwargs: dict = {"limit": limit}
        if _continue:
            kwargs["_continue"] = _continue
        result = self.rbac_v1.list_namespaced_role(namespace, **kwargs)
        items = [
            {
                "name": r.metadata.name,
                "namespace": r.metadata.namespace,
                "rules": [_rule_from_k8s(rule) for rule in (r.rules or [])],
                "is_system": False,
            }
            for r in result.items
        ]
        return {
            "items": items,
            "total": len(items),
            "next_continue": result.metadata._continue,
        }

    def create_role(self, namespace: str, name: str, rules: list[PolicyRule]) -> dict:
        role = client.V1Role(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"managed-by": "clustervision"},
            ),
            rules=[_rule_to_k8s(r) for r in rules],
        )
        created = self.rbac_v1.create_namespaced_role(namespace, role)
        return {"name": created.metadata.name, "namespace": namespace}

    def update_role(self, namespace: str, name: str, rules: list[PolicyRule]) -> dict:
        role = self.rbac_v1.read_namespaced_role(name, namespace)
        role.rules = [_rule_to_k8s(r) for r in rules]
        updated = self.rbac_v1.replace_namespaced_role(name, namespace, role)
        return {
            "name": updated.metadata.name,
            "namespace": updated.metadata.namespace,
            "rules": [_rule_from_k8s(r) for r in (updated.rules or [])],
            "is_system": False,
        }

    def delete_role(self, namespace: str, name: str):
        self.rbac_v1.delete_namespaced_role(name, namespace)

    # ── ClusterRoleBindings ─────────────────────────────────────────────────

    def list_cluster_role_bindings(
        self,
        limit: int = 500,
        _continue: Optional[str] = None,
    ) -> dict:
        kwargs: dict = {"limit": limit}
        if _continue:
            kwargs["_continue"] = _continue
        result = self.rbac_v1.list_cluster_role_binding(**kwargs)
        items = [
            {
                "name": crb.metadata.name,
                "namespace": None,
                "role_ref": crb.role_ref.name,
                "role_kind": crb.role_ref.kind,
                "subjects": [_subject_from_k8s(s) for s in (crb.subjects or [])],
            }
            for crb in result.items
        ]
        return {
            "items": items,
            "total": len(items),
            "next_continue": result.metadata._continue,
        }

    def create_cluster_role_binding(
        self, name: str, role_name: str, subjects: list[Subject]
    ) -> dict:
        crb = client.V1ClusterRoleBinding(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={"managed-by": "clustervision"},
            ),
            role_ref=client.V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="ClusterRole",
                name=role_name,
            ),
            subjects=[_subject_to_k8s(s) for s in subjects],
        )
        created = self.rbac_v1.create_cluster_role_binding(crb)
        return {"name": created.metadata.name}

    def delete_cluster_role_binding(self, name: str):
        self.rbac_v1.delete_cluster_role_binding(name)

    # ── RoleBindings ────────────────────────────────────────────────────────

    def list_role_bindings(self, namespace: str) -> list[dict]:
        rbs = self.rbac_v1.list_namespaced_role_binding(namespace)
        return [
            {
                "name": rb.metadata.name,
                "namespace": rb.metadata.namespace,
                "role_ref": rb.role_ref.name,
                "role_kind": rb.role_ref.kind,
                "subjects": [_subject_from_k8s(s) for s in (rb.subjects or [])],
            }
            for rb in rbs.items
        ]

    def create_role_binding(
        self,
        namespace: str,
        name: str,
        role_name: str,
        role_kind: str,
        subjects: list[Subject],
    ) -> dict:
        rb = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"managed-by": "clustervision"},
            ),
            role_ref=client.V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind=role_kind,
                name=role_name,
            ),
            subjects=[_subject_to_k8s(s) for s in subjects],
        )
        created = self.rbac_v1.create_namespaced_role_binding(namespace, rb)
        return {"name": created.metadata.name, "namespace": namespace}

    def delete_role_binding(self, namespace: str, name: str):
        self.rbac_v1.delete_namespaced_role_binding(name, namespace)

    # ── Internal pagination helpers ─────────────────────────────────────────

    def _iter_all_crbs(self, page_size: int = 500):
        """Yield every ClusterRoleBinding, following continuation tokens."""
        cursor = None
        while True:
            kwargs: dict = {"limit": page_size}
            if cursor:
                kwargs["_continue"] = cursor
            result = self.rbac_v1.list_cluster_role_binding(**kwargs)
            yield from result.items
            cursor = result.metadata._continue
            if not cursor:
                break

    def _iter_all_rbs(self, page_size: int = 500):
        """Yield every RoleBinding across all namespaces, following continuation tokens."""
        cursor = None
        while True:
            kwargs: dict = {"limit": page_size}
            if cursor:
                kwargs["_continue"] = cursor
            result = self.rbac_v1.list_role_binding_for_all_namespaces(**kwargs)
            yield from result.items
            cursor = result.metadata._continue
            if not cursor:
                break

    # ── Binding cache (TTL 60s) ──────────────────────────────────────────────

    _crb_cache: list = []
    _crb_cache_at: float = 0.0
    _rb_cache: list = []
    _rb_cache_at: float = 0.0
    _CACHE_TTL = 60.0

    def _get_all_crbs(self) -> list:
        if time.monotonic() - self._crb_cache_at < self._CACHE_TTL:
            return self._crb_cache
        items = list(self._iter_all_crbs())
        self.__class__._crb_cache = items
        self.__class__._crb_cache_at = time.monotonic()
        return items

    def _get_all_rbs(self) -> list:
        if time.monotonic() - self._rb_cache_at < self._CACHE_TTL:
            return self._rb_cache
        items = list(self._iter_all_rbs())
        self.__class__._rb_cache = items
        self.__class__._rb_cache_at = time.monotonic()
        return items

    def _invalidate_binding_cache(self):
        self.__class__._crb_cache_at = 0.0
        self.__class__._rb_cache_at = 0.0

    # ── User-centric convenience methods ────────────────────────────────────

    def get_user_permissions(self, username: str) -> dict:
        # Fetch CRBs and RoleBindings in parallel — they are independent K8s calls
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_crbs = pool.submit(self._get_all_crbs)
            fut_rbs = pool.submit(self._get_all_rbs)
            all_crbs = fut_crbs.result()
            all_rbs = fut_rbs.result()

        cluster_bindings = []
        for crb in all_crbs:
            subjects = crb.subjects or []
            if any(s.name == username and s.kind in ("User", "ServiceAccount") for s in subjects):
                cluster_bindings.append({
                    "name": crb.metadata.name,
                    "namespace": None,
                    "role_ref": crb.role_ref.name,
                    "role_kind": crb.role_ref.kind,
                    "subjects": [_subject_from_k8s(s) for s in subjects],
                })

        namespace_bindings = []
        for rb in all_rbs:
            subjects = rb.subjects or []
            if any(s.name == username and s.kind in ("User", "ServiceAccount") for s in subjects):
                namespace_bindings.append({
                    "name": rb.metadata.name,
                    "namespace": rb.metadata.namespace,
                    "role_ref": rb.role_ref.name,
                    "role_kind": rb.role_ref.kind,
                    "subjects": [_subject_from_k8s(s) for s in subjects],
                })

        return {
            "username": username,
            "cluster_bindings": cluster_bindings,
            "namespace_bindings": namespace_bindings,
        }

    def assign_role(
        self,
        username: str,
        user_kind: str,
        role_name: str,
        role_kind: str,
        namespace: Optional[str] = None,
        sa_namespace: Optional[str] = None,
    ):
        """Assign a role to a user. Creates or patches the appropriate binding.

        Uses PATCH (strategic merge) instead of read+replace to avoid the race
        condition where two concurrent requests overwrite each other's subjects.
        Kubernetes merges subjects by name, so sending only the new subject is safe.
        """
        subject = Subject(
            kind=SubjectKind(user_kind),
            name=username,
            namespace=sa_namespace,
        )
        binding_name = f"clustervision-{username}-{role_name}"
        patch_body = {"subjects": [_subject_to_k8s(subject)]}

        if namespace is None and role_kind == "ClusterRole":
            try:
                self.rbac_v1.patch_cluster_role_binding(binding_name, patch_body)
            except ApiException as e:
                if e.status == 404:
                    self.create_cluster_role_binding(binding_name, role_name, [subject])
                else:
                    raise
        else:
            ns = namespace or "default"
            try:
                self.rbac_v1.patch_namespaced_role_binding(binding_name, ns, patch_body)
            except ApiException as e:
                if e.status == 404:
                    self.create_role_binding(ns, binding_name, role_name, role_kind, [subject])
                else:
                    raise
        self._invalidate_binding_cache()

    def revoke_role(
        self,
        username: str,
        role_name: str,
        namespace: Optional[str] = None,
    ):
        """Remove a user from all bindings referencing the given role."""
        binding_name = f"clustervision-{username}-{role_name}"
        if namespace is None:
            try:
                self.rbac_v1.delete_cluster_role_binding(binding_name)
            except ApiException as e:
                if e.status != 404:
                    raise
        else:
            try:
                self.rbac_v1.delete_namespaced_role_binding(binding_name, namespace)
            except ApiException as e:
                if e.status != 404:
                    raise
        self._invalidate_binding_cache()

    def delete_user_bindings(self, username: str):
        """Delete all ClusterVision-managed bindings that reference this user."""
        prefix = f"clustervision-{username}-"

        for crb in self._iter_all_crbs():
            if not crb.metadata.name.startswith(prefix):
                continue
            try:
                self.rbac_v1.delete_cluster_role_binding(crb.metadata.name)
                logger.info("Deleted ClusterRoleBinding %s", crb.metadata.name)
            except ApiException as e:
                if e.status != 404:
                    raise

        for rb in self._iter_all_rbs():
            if not rb.metadata.name.startswith(prefix):
                continue
            try:
                self.rbac_v1.delete_namespaced_role_binding(rb.metadata.name, rb.metadata.namespace)
                logger.info("Deleted RoleBinding %s/%s", rb.metadata.namespace, rb.metadata.name)
            except ApiException as e:
                if e.status != 404:
                    raise
        self._invalidate_binding_cache()

    # ── Namespaces ──────────────────────────────────────────────────────────

    def list_namespaces(self) -> list[str]:
        return [ns.metadata.name for ns in self.core_v1.list_namespace().items]

    # ── Namespace access view ────────────────────────────────────────────────

    def get_namespace_access(self, namespace: str) -> list[dict]:
        results = []

        # RoleBindings scoped to this namespace
        rbs = self.rbac_v1.list_namespaced_role_binding(namespace)
        for rb in rbs.items:
            for subject in (rb.subjects or []):
                results.append({
                    "subject": subject.name,
                    "subject_kind": subject.kind,
                    "subject_namespace": subject.namespace,
                    "role": rb.role_ref.name,
                    "role_kind": rb.role_ref.kind,
                    "binding": rb.metadata.name,
                    "scope": "namespace",
                })

        # ClusterRoleBindings apply cluster-wide (include this namespace)
        for crb in self._get_all_crbs():
            for subject in (crb.subjects or []):
                results.append({
                    "subject": subject.name,
                    "subject_kind": subject.kind,
                    "subject_namespace": subject.namespace,
                    "role": crb.role_ref.name,
                    "role_kind": crb.role_ref.kind,
                    "binding": crb.metadata.name,
                    "scope": "cluster",
                })

        return results

    # ── Access simulator (SubjectAccessReview) ───────────────────────────────

    def check_access(
        self,
        user: str,
        verb: str,
        resource: str,
        namespace: Optional[str],
        api_group: str = "",
    ) -> dict:
        sar = self.auth_v1.create_subject_access_review(
            client.V1SubjectAccessReview(
                spec=client.V1SubjectAccessReviewSpec(
                    user=user,
                    resource_attributes=client.V1ResourceAttributes(
                        verb=verb,
                        resource=resource,
                        namespace=namespace,
                        group=api_group,
                    ),
                )
            )
        )
        return {
            "allowed": sar.status.allowed,
            "denied": sar.status.denied or False,
            "reason": sar.status.reason or "",
        }
