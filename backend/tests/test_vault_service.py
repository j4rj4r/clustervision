import pytest

from app.services import vault_service


@pytest.fixture(autouse=True)
def reset_vault_singleton():
    """_vault_svc/_last_sync are module-level globals shared across the whole
    process (multi-worker sync design) — reset them so tests don't leak
    state into each other."""
    vault_service._vault_svc = None
    vault_service._last_sync = 0.0
    yield
    vault_service._vault_svc = None
    vault_service._last_sync = 0.0


def test_read_config_row_none_when_never_configured(db_session):
    assert vault_service._read_config_row() is None


def test_write_then_read_config_row(db_session):
    vault_service._write_config_row({
        "addr": "https://vault.example.com", "token": "hvs.xxx", "mount": "secret",
        "base_path": "cv/users", "namespace": "", "tls_skip_verify": False,
    })
    cfg = vault_service._read_config_row()
    assert cfg["addr"] == "https://vault.example.com"
    assert cfg["token"] == "hvs.xxx"


def test_disable_marks_enabled_false(db_session):
    vault_service._write_config_row({"addr": "https://x", "token": "t"})
    vault_service._write_config_row({"enabled": False})
    assert vault_service._read_config_row() == {"enabled": False}


def test_configure_vault_creates_working_singleton(db_session):
    svc = vault_service.configure_vault(
        addr="https://vault.example.com", token="hvs.xxx", mount="secret",
        base_path="cv/users", namespace="", tls_skip_verify=True,
    )
    assert svc is not None
    assert svc.addr == "https://vault.example.com"
    assert svc.tls_skip_verify is True
    assert vault_service.get_vault_service() is svc


def test_disable_vault_clears_singleton(db_session):
    vault_service.configure_vault(addr="https://x", token="t", mount="secret", base_path="p", namespace="")
    vault_service.disable_vault()
    assert vault_service.get_vault_service() is None


def test_apply_config_rejects_incomplete_credentials(db_session):
    vault_service._apply_config({"addr": "https://x", "token": ""})  # no token
    assert vault_service._vault_svc is None


def test_apply_config_keeps_cached_health_when_unchanged(db_session):
    first = vault_service.configure_vault(addr="https://x", token="t", mount="secret", base_path="p", namespace="")
    first._cached_healthy = True  # simulate a prior health_check() result
    vault_service._apply_config(vault_service._read_config_row())
    assert vault_service._vault_svc is first  # same instance, cached health preserved
