import logging
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

    # ── ClusterRoles ────────────────────────────────────────────────────────

    def list_cluster_roles(self, include_system: bool = False) -> list[dict]:
        roles = self.rbac_v1.list_cluster_role()
        result = []
        for r in roles.items:
            is_system = r.metadata.name.startswith("system:") or r.metadata.name.startswith("kubeadm:")
            if not include_system and is_system:
                continue
            result.append({
                "name": r.metadata.name,
                "rules": [_rule_from_k8s(rule) for rule in (r.rules or [])],
                "is_system": is_system,
            })
        return result

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

    def delete_cluster_role(self, name: str):
        self.rbac_v1.delete_cluster_role(name)

    # ── Namespaced Roles ────────────────────────────────────────────────────

    def list_roles(self, namespace: str) -> list[dict]:
        roles = self.rbac_v1.list_namespaced_role(namespace)
        return [
            {
                "name": r.metadata.name,
                "namespace": r.metadata.namespace,
                "rules": [_rule_from_k8s(rule) for rule in (r.rules or [])],
                "is_system": False,
            }
            for r in roles.items
        ]

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

    def delete_role(self, namespace: str, name: str):
        self.rbac_v1.delete_namespaced_role(name, namespace)

    # ── ClusterRoleBindings ─────────────────────────────────────────────────

    def list_cluster_role_bindings(self) -> list[dict]:
        crbs = self.rbac_v1.list_cluster_role_binding()
        return [
            {
                "name": crb.metadata.name,
                "namespace": None,
                "role_ref": crb.role_ref.name,
                "role_kind": crb.role_ref.kind,
                "subjects": [_subject_from_k8s(s) for s in (crb.subjects or [])],
            }
            for crb in crbs.items
        ]

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

    # ── User-centric convenience methods ────────────────────────────────────

    def get_user_permissions(self, username: str) -> dict:
        # 1 call for all CRBs
        crbs = self.rbac_v1.list_cluster_role_binding()
        cluster_bindings = []
        for crb in crbs.items:
            subjects = crb.subjects or []
            if any(s.name == username and s.kind in ("User", "ServiceAccount") for s in subjects):
                cluster_bindings.append({
                    "name": crb.metadata.name,
                    "namespace": None,
                    "role_ref": crb.role_ref.name,
                    "role_kind": crb.role_ref.kind,
                    "subjects": [_subject_from_k8s(s) for s in subjects],
                })

        # 1 call for all RoleBindings across all namespaces (instead of 1 per namespace)
        rbs = self.rbac_v1.list_role_binding_for_all_namespaces()
        namespace_bindings = []
        for rb in rbs.items:
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
        """Assign a role to a user. Creates or updates the appropriate binding."""
        subject = Subject(
            kind=SubjectKind(user_kind),
            name=username,
            namespace=sa_namespace,
        )
        binding_name = f"clustervision-{username}-{role_name}"

        if namespace is None and role_kind == "ClusterRole":
            # ClusterRoleBinding
            try:
                existing = self.rbac_v1.read_cluster_role_binding(binding_name)
                current_subjects = [_subject_from_k8s(s) for s in (existing.subjects or [])]
                if not any(s["name"] == username for s in current_subjects):
                    current_subjects.append(subject.model_dump())
                    existing.subjects = [_subject_to_k8s(Subject(**s)) for s in current_subjects]
                    self.rbac_v1.replace_cluster_role_binding(binding_name, existing)
            except ApiException as e:
                if e.status == 404:
                    self.create_cluster_role_binding(binding_name, role_name, [subject])
                else:
                    raise
        else:
            # RoleBinding in namespace
            ns = namespace or "default"
            try:
                existing = self.rbac_v1.read_namespaced_role_binding(binding_name, ns)
                current_subjects = [_subject_from_k8s(s) for s in (existing.subjects or [])]
                if not any(s["name"] == username for s in current_subjects):
                    current_subjects.append(subject.model_dump())
                    existing.subjects = [_subject_to_k8s(Subject(**s)) for s in current_subjects]
                    self.rbac_v1.replace_namespaced_role_binding(binding_name, ns, existing)
            except ApiException as e:
                if e.status == 404:
                    self.create_role_binding(ns, binding_name, role_name, role_kind, [subject])
                else:
                    raise

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

    # ── Namespaces ──────────────────────────────────────────────────────────

    def list_namespaces(self) -> list[str]:
        return [ns.metadata.name for ns in self.core_v1.list_namespace().items]
