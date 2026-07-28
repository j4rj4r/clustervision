import logging
import ssl
from dataclasses import dataclass

import ldap3
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LdapAuthResult:
    username: str
    role: str


def authenticate(username: str, password: str) -> LdapAuthResult | None:
    """Search-then-bind against Active Directory: bind as the configured
    service account to find the user's DN and group membership, then re-bind
    as the user to verify their password. Returns None on any failure
    (unreachable server, unknown user, bad password, not in an allowed
    group) — callers don't need to distinguish why."""
    settings = get_settings()
    if not settings.ldap_enabled:
        return None
    if not password:
        return None

    tls = ldap3.Tls(
        validate=ssl.CERT_NONE if settings.ldap_tls_skip_verify else ssl.CERT_REQUIRED,
    )
    server = ldap3.Server(
        settings.ldap_url,
        use_ssl=settings.ldap_url.startswith("ldaps://"),
        tls=tls,
        connect_timeout=5,
    )

    try:
        search_conn = ldap3.Connection(
            server,
            user=settings.ldap_bind_dn,
            password=settings.ldap_bind_password,
            auto_bind=True,
            receive_timeout=5,
        )
    except LDAPException as e:
        logger.warning("LDAP service-account bind failed: %s", e)
        return None

    try:
        search_filter = settings.ldap_user_search_filter.format(username=escape_filter_chars(username))
        search_conn.search(
            settings.ldap_user_search_base,
            search_filter,
            attributes=["distinguishedName", "memberOf"],
        )
        if not search_conn.entries:
            return None
        entry = search_conn.entries[0]
        user_dn = str(entry.entry_dn)
        groups = [str(g) for g in entry.memberOf] if "memberOf" in entry else []
    finally:
        search_conn.unbind()

    try:
        user_conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True, receive_timeout=5)
        user_conn.unbind()
    except LDAPException:
        return None  # wrong password, or the account can't bind (locked/disabled)

    if settings.ldap_admin_group_dn and settings.ldap_admin_group_dn in groups:
        role = "admin"
    elif not settings.ldap_viewer_group_dn or settings.ldap_viewer_group_dn in groups:
        role = "viewer"
    else:
        logger.info("LDAP user %s authenticated but is in no allowed group — denied", username)
        return None

    return LdapAuthResult(username=username, role=role)
