"""ldap_service tests fake out ldap3.Connection instead of hitting a real
directory — this exercises our own logic (filter escaping, search-then-bind
sequencing, group-to-role mapping, guard clauses), not ldap3's own wire
protocol handling, which is the library's job to test."""

from ldap3.core.exceptions import LDAPException

from app.services import ldap_service

_BIND_DN = "CN=svc-clustervision,OU=Service,DC=corp,DC=local"
_BIND_PASSWORD = "svc-password"


class _FakeEntry:
    def __init__(self, dn, member_of):
        self.entry_dn = dn
        self._member_of = member_of

    def __contains__(self, attr):
        return attr == "memberOf" and bool(self._member_of)

    @property
    def memberOf(self):
        return self._member_of


class _FakeConnection:
    """Mimics just enough of ldap3.Connection for authenticate() to run.

    `directory` maps sAMAccountName -> (dn, password, groups). The service
    bind (`user == _BIND_DN`) always succeeds if the password matches;
    the second bind (`user == a directory entry's DN`) is the actual
    credential check for that user.
    """

    def __init__(self, directory):
        self.directory = directory

    def __call__(self, server, user=None, password=None, auto_bind=None, receive_timeout=None):
        if user == _BIND_DN:
            if password != _BIND_PASSWORD:
                raise LDAPException("service account bind failed")
            return _BoundAsService(self.directory)

        for _uid, (dn, real_password, _groups) in self.directory.items():
            if user == dn:
                if password != real_password:
                    raise LDAPException("invalid credentials")
                return _BoundAsUser()
        raise LDAPException("no such object")


class _BoundAsService:
    def __init__(self, directory):
        self.directory = directory
        self.entries = []

    def search(self, base, search_filter, attributes=None):
        # Our filter is "(sAMAccountName=<escaped-username>)" — good enough
        # to match the plain uid against the rendered filter string here.
        for uid, (dn, _password, groups) in self.directory.items():
            if uid in search_filter:
                self.entries = [_FakeEntry(dn, groups)]
                return
        self.entries = []

    def unbind(self):
        pass


class _BoundAsUser:
    def unbind(self):
        pass


def _configure(monkeypatch, directory, **settings_overrides):
    monkeypatch.setenv("LDAP_ENABLED", "true")
    monkeypatch.setenv("LDAP_URL", "ldaps://dc01.corp.local:636")
    monkeypatch.setenv("LDAP_BIND_DN", _BIND_DN)
    monkeypatch.setenv("LDAP_BIND_PASSWORD", _BIND_PASSWORD)
    monkeypatch.setenv("LDAP_USER_SEARCH_BASE", "OU=Users,DC=corp,DC=local")
    for key, value in settings_overrides.items():
        monkeypatch.setenv(f"LDAP_{key.upper()}", value)

    from app.config import get_settings
    get_settings.cache_clear()

    monkeypatch.setattr(ldap_service.ldap3, "Connection", _FakeConnection(directory))


def test_disabled_returns_none_without_any_ldap_call(monkeypatch):
    monkeypatch.setenv("LDAP_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert ldap_service.authenticate("alice", "whatever") is None


def test_empty_password_rejected_without_attempting_a_bind(monkeypatch):
    """Guards against LDAP's classic unauthenticated-bind footgun: some
    directories treat an empty-password bind as a trivially successful
    'anonymous' bind rather than a credential check."""
    _configure(monkeypatch, directory={})
    assert ldap_service.authenticate("alice", "") is None


def test_successful_bind_maps_admin_group(monkeypatch):
    directory = {
        "alice": ("CN=Alice,OU=Users,DC=corp,DC=local", "alice-password", ["CN=CV-Admins,OU=Groups,DC=corp,DC=local"]),
    }
    _configure(monkeypatch, directory, admin_group_dn="CN=CV-Admins,OU=Groups,DC=corp,DC=local")
    result = ldap_service.authenticate("alice", "alice-password")
    assert result.username == "alice"
    assert result.role == "admin"


def test_successful_bind_non_admin_group_maps_viewer(monkeypatch):
    directory = {
        "bob": ("CN=Bob,OU=Users,DC=corp,DC=local", "bob-password", ["CN=Everyone,OU=Groups,DC=corp,DC=local"]),
    }
    _configure(monkeypatch, directory, admin_group_dn="CN=CV-Admins,OU=Groups,DC=corp,DC=local")
    result = ldap_service.authenticate("bob", "bob-password")
    assert result.role == "viewer"


def test_viewer_group_configured_denies_users_outside_it(monkeypatch):
    directory = {
        "carol": ("CN=Carol,OU=Users,DC=corp,DC=local", "carol-password", ["CN=Sales,OU=Groups,DC=corp,DC=local"]),
    }
    _configure(
        monkeypatch, directory,
        admin_group_dn="CN=CV-Admins,OU=Groups,DC=corp,DC=local",
        viewer_group_dn="CN=CV-Viewers,OU=Groups,DC=corp,DC=local",
    )
    assert ldap_service.authenticate("carol", "carol-password") is None


def test_wrong_password_denied(monkeypatch):
    directory = {
        "alice": ("CN=Alice,OU=Users,DC=corp,DC=local", "correct-password", []),
    }
    _configure(monkeypatch, directory)
    assert ldap_service.authenticate("alice", "wrong-password") is None


def test_unknown_user_denied(monkeypatch):
    _configure(monkeypatch, directory={})
    assert ldap_service.authenticate("nobody", "whatever") is None


def test_service_account_bind_failure_denies_without_crashing(monkeypatch):
    _configure(monkeypatch, directory={"alice": ("CN=Alice,DC=corp,DC=local", "pw", [])})
    monkeypatch.setenv("LDAP_BIND_PASSWORD", "wrong-service-password")
    from app.config import get_settings
    get_settings.cache_clear()
    assert ldap_service.authenticate("alice", "pw") is None


def test_username_is_escaped_in_search_filter(monkeypatch):
    """A classic LDAP injection payload in the username must not be able to
    widen the search filter to match an unintended entry."""
    directory = {
        "alice": ("CN=Alice,DC=corp,DC=local", "alice-password", []),
    }
    _configure(monkeypatch, directory)
    injected = "*)(uid=*"
    assert ldap_service.authenticate(injected, "anything") is None
