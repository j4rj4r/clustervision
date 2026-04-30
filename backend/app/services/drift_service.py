import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Deque

from kubernetes import client, watch
from kubernetes.client.exceptions import ApiException

logger = logging.getLogger(__name__)

CV_LABEL = "managed-by"
CV_LABEL_VALUE = "clustervision"
CV_PREFIX = "clustervision-"
MAX_EVENTS = 200


class DriftEvent:
    def __init__(self, kind: str, binding_name: str, namespace: str | None, detail: str):
        self.kind = kind  # "external_modification" | "label_stripped" | "orphaned"
        self.binding_name = binding_name
        self.namespace = namespace
        self.detail = detail
        self.detected_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "binding_name": self.binding_name,
            "namespace": self.namespace,
            "detail": self.detail,
            "detected_at": self.detected_at,
        }


class DriftService:
    def __init__(self, api_client: client.ApiClient):
        self.rbac_v1 = client.RbacAuthorizationV1Api(api_client)
        self._events: Deque[DriftEvent] = deque(maxlen=MAX_EVENTS)
        # Binding names written by ClusterVision within the last 30s — excluded from drift
        self._cv_writes: dict[str, float] = {}

    # ── Called by ClusterVision before it writes a binding ─────────────────

    def mark_cv_write(self, binding_name: str) -> None:
        import time
        self._cv_writes[binding_name] = time.time()

    def _is_cv_write(self, binding_name: str) -> bool:
        import time
        ts = self._cv_writes.get(binding_name)
        if ts and time.time() - ts < 30:
            return True
        self._cv_writes.pop(binding_name, None)
        return False

    # ── Periodic scan ───────────────────────────────────────────────────────

    def scan(self) -> list[dict]:
        """Detect drift by comparing K8s state vs ClusterVision expectations."""
        new_events = []

        # 1. CV-prefixed bindings without the managed-by label → label was stripped externally
        try:
            crbs = self.rbac_v1.list_cluster_role_binding(label_selector=f"!{CV_LABEL}").items
            for crb in crbs:
                if crb.metadata.name.startswith(CV_PREFIX) and not self._is_cv_write(crb.metadata.name):
                    evt = DriftEvent(
                        kind="label_stripped",
                        binding_name=crb.metadata.name,
                        namespace=None,
                        detail=f"ClusterRoleBinding '{crb.metadata.name}' has ClusterVision prefix but is missing the managed-by label — may have been modified externally.",
                    )
                    if not self._already_known(crb.metadata.name):
                        self._events.appendleft(evt)
                        new_events.append(evt.to_dict())
        except ApiException as e:
            logger.warning("Drift scan CRB label check failed: %s", e)

        try:
            rbs = self.rbac_v1.list_role_binding_for_all_namespaces(label_selector=f"!{CV_LABEL}").items
            for rb in rbs:
                if rb.metadata.name.startswith(CV_PREFIX) and not self._is_cv_write(rb.metadata.name):
                    evt = DriftEvent(
                        kind="label_stripped",
                        binding_name=rb.metadata.name,
                        namespace=rb.metadata.namespace,
                        detail=f"RoleBinding '{rb.metadata.name}' in namespace '{rb.metadata.namespace}' has ClusterVision prefix but is missing the managed-by label.",
                    )
                    if not self._already_known(rb.metadata.name):
                        self._events.appendleft(evt)
                        new_events.append(evt.to_dict())
        except ApiException as e:
            logger.warning("Drift scan RB label check failed: %s", e)

        return new_events

    def _already_known(self, binding_name: str) -> bool:
        return any(e.binding_name == binding_name for e in self._events)

    # ── Watch (real-time) ───────────────────────────────────────────────────

    async def watch_loop(self) -> None:
        """Watch ClusterRoleBindings and RoleBindings for external modifications."""
        loop = asyncio.get_running_loop()
        await asyncio.gather(
            loop.run_in_executor(None, self._watch_crbs),
            loop.run_in_executor(None, self._watch_rbs),
        )

    def _watch_crbs(self) -> None:
        w = watch.Watch()
        try:
            for event in w.stream(
                self.rbac_v1.list_cluster_role_binding,
                label_selector=f"{CV_LABEL}={CV_LABEL_VALUE}",
                timeout_seconds=0,
            ):
                etype = event["type"]
                obj = event["object"]
                name = obj.metadata.name
                if etype == "MODIFIED" and not self._is_cv_write(name):
                    evt = DriftEvent(
                        kind="external_modification",
                        binding_name=name,
                        namespace=None,
                        detail=f"ClusterRoleBinding '{name}' was modified outside ClusterVision.",
                    )
                    if not self._already_known(name):
                        self._events.appendleft(evt)
                        logger.warning("RBAC drift detected: %s", evt.detail)
        except Exception as e:
            logger.warning("CRB watch ended: %s", e)

    def _watch_rbs(self) -> None:
        w = watch.Watch()
        try:
            for event in w.stream(
                self.rbac_v1.list_role_binding_for_all_namespaces,
                label_selector=f"{CV_LABEL}={CV_LABEL_VALUE}",
                timeout_seconds=0,
            ):
                etype = event["type"]
                obj = event["object"]
                name = obj.metadata.name
                ns = obj.metadata.namespace
                if etype == "MODIFIED" and not self._is_cv_write(name):
                    evt = DriftEvent(
                        kind="external_modification",
                        binding_name=name,
                        namespace=ns,
                        detail=f"RoleBinding '{name}' in namespace '{ns}' was modified outside ClusterVision.",
                    )
                    if not self._already_known(name):
                        self._events.appendleft(evt)
                        logger.warning("RBAC drift detected: %s", evt.detail)
        except Exception as e:
            logger.warning("RB watch ended: %s", e)

    # ── Public accessors ────────────────────────────────────────────────────

    def get_events(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in list(self._events)[:limit]]

    def clear(self) -> None:
        self._events.clear()

    @property
    def event_count(self) -> int:
        return len(self._events)
