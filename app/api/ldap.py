import ldap3
from ..settings import (
    LDAP_HOST,
    LDAP_PORT,
    LDAP_USE_SSL,
    LDAP_USER_RDN_ATTR,
    LDAP_BASE_DN,
    LDAP_USER_DN,
)


def authenticate_user(username: str, password: str) -> bool:
    """Return True if the authentication is successful, False otherwise"""
    server = ldap3.Server(LDAP_HOST, port=LDAP_PORT, use_ssl=LDAP_USE_SSL)
    if LDAP_USER_DN:
        user_search_dn = f"{LDAP_USER_DN},{LDAP_BASE_DN}"
    else:
        user_search_dn = LDAP_BASE_DN
    bind_user = f"{LDAP_USER_RDN_ATTR}={username},{user_search_dn}"
    connection = ldap3.Connection(
        server=server,
        user=bind_user,
        password=password,
        client_strategy=ldap3.SYNC,
        authentication="SIMPLE",
        raise_exceptions=False,
    )
    result = connection.bind()
    connection.unbind()
    return result
