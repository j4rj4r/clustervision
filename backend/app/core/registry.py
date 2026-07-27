from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, select

from ..db.models import ManagedUser


class RegistryMixin:
    """Managed-user registry (certificate + ServiceAccount users), backed by
    the `managed_users` table.

    Requires subclasses to expose:
      - self.db : sqlalchemy.orm.Session
    """

    def _load_registry(self) -> list[dict]:
        rows = self.db.scalars(select(ManagedUser)).all()
        return [r.to_dict() for r in rows]

    def _update_registry(self, mutate: Callable[[list[dict]], list[dict]]) -> list[dict]:
        """Replace the registry with `mutate(current)`. `mutate` receives the
        current user list and returns the new one — same contract as the
        ConfigMap-backed version this replaces, so callers (which do their own
        consistency checks — duplicates, existence — against the input) don't
        need to change.

        Diffs the before/after lists into targeted inserts/updates/deletes
        rather than truncating the table, so concurrent unrelated writes don't
        race each other away.
        """
        before = {(u["name"], u.get("namespace", "default")): u for u in self._load_registry()}
        after_list = mutate(list(before.values()))
        after = {(u["name"], u.get("namespace", "default")): u for u in after_list}

        for key in before.keys() - after.keys():
            name, namespace = key
            self.db.execute(delete(ManagedUser).where(ManagedUser.name == name, ManagedUser.namespace == namespace))

        for key, u in after.items():
            name, namespace = key
            created_at = u.get("created_at")
            cert_expiry = u.get("cert_expiry")
            values = {
                "type": u["type"],
                "groups_csv": ",".join(u.get("groups") or []),
                "created_at": datetime.fromisoformat(created_at) if created_at else datetime.now(UTC),
                "csr_name": u.get("csr_name"),
                "cert_expiry": datetime.fromisoformat(cert_expiry) if cert_expiry else None,
                "imported": bool(u.get("imported", False)),
            }
            existing = self.db.get(ManagedUser, (name, namespace))
            if existing is None:
                self.db.add(ManagedUser(name=name, namespace=namespace, **values))
            elif before.get(key) != u:
                for k, v in values.items():
                    setattr(existing, k, v)

        self.db.commit()
        return after_list
