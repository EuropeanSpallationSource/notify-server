from starlette.config import Config
from starlette.datastructures import Secret, CommaSeparatedStrings

# Config will be read from environment variables and/or ".env" files.
config = Config(".env")

LDAP_HOST = config("LDAP_HOST", cast=str, default="ldap.example.org")
LDAP_PORT = config("LDAP_PORT", cast=int, default=636)
LDAP_USE_SSL = config("LDAP_USE_SSL", cast=bool, default=True)
LDAP_BASE_DN = config("LDAP_BASE_DN", cast=str, default="DC=esss,DC=lu,DC=se")
LDAP_USER_DN = config("LDAP_USER_DN", cast=str, default="")
LDAP_USER_RDN_ATTR = config("LDAP_USER_RDN_ATTR", cast=str, default="uid")
ADMIN_USERS = config("ADMIN_USERS", cast=CommaSeparatedStrings, default="")
SQLALCHEMY_DATABASE_URL = config(
    "SQLALCHEMY_DATABASE_URL", cast=str, default="sqlite:///./sql_app.db"
)
ALGORITHM = "ES256"
APNS_KEY_ID = config("APNS_KEY_ID", cast=Secret, default="key-id")
APNS_AUTH_KEY = config("APNS_AUTH_KEY", cast=Secret, default="key")
TEAM_ID = config("TEAM_ID", cast=Secret, default="team")
APPLE_SERVER = config(
    "APPLE_SERVER", cast=str, default="api.development.push.apple.com:443"
)
BUNDLE_ID = "eu.ess.ESS-Notify"
