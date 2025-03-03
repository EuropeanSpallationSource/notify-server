from starlette.config import Config
from starlette.datastructures import Secret, CommaSeparatedStrings

DUMMY_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgtAParbMemenK/+8T
JYWanX1jzKaFcgmupVALPHyaKKKhRANCAARVmMAXI+WPS/vjIsFBHb3B5dQKqgT8
ytZPnlbWNLGGR7tKdB1eLzyBlIVFe9El4Wlvs19ACPRMtE7l75IlbOT+
-----END PRIVATE KEY-----
"""

# Config will be read from environment variables and/or ".env" files.
try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

# Should be set to "ldap" or "url"
# This is still supported for the API even when OIDC is enabled
AUTHENTICATION_METHOD = config("AUTHENTICATION_METHOD", cast=str, default="ldap")
# LDAP configuration
LDAP_HOST = config("LDAP_HOST", cast=str, default="ldap.example.org")
LDAP_PORT = config("LDAP_PORT", cast=int, default=636)
LDAP_USE_SSL = config("LDAP_USE_SSL", cast=bool, default=True)
LDAP_BASE_DN = config("LDAP_BASE_DN", cast=str, default="DC=esss,DC=lu,DC=se")
LDAP_USER_DN = config("LDAP_USER_DN", cast=str, default="")
LDAP_USER_RDN_ATTR = config("LDAP_USER_RDN_ATTR", cast=str, default="uid")

# OpenID Connect configuration
# When enabled OIDC will be used for:
# - web login (only method supported)
# - API login (old authentication method still supported as well)
OIDC_ENABLED = config("OIDC_ENABLED", cast=bool, default=False)
OIDC_NAME = config("OIDC_NAME", cast=str, default="keycloak")
OIDC_SERVER_URL = config(
    "OIDC_SERVER_URL",
    cast=str,
    default="https://keycloak.example.org/auth/realms/myrealm/.well-known/openid-configuration",
)
OIDC_CLIENT_ID = config("OIDC_CLIENT_ID", cast=str, default="notify")
OIDC_CLIENT_SECRET = config("OIDC_CLIENT_SECRET", cast=Secret, default="!secret")
OIDC_SCOPE = config("OIDC_SCOPE", cast=str, default="openid email profile")

# URL to use when AUTHENTICATION_METHOD is set to "url"
AUTHENTICATION_URL = config(
    "AUTHENTICATION_URL", cast=str, default="https//auth.example.org/login"
)
ADMIN_USERS = config("ADMIN_USERS", cast=CommaSeparatedStrings, default="")
# Demo account with "demo" username has access only to service defined in DEMO_ACCOUNT_SERVICE
DEMO_ACCOUNT_SERVICE = config("DEMO_ACCOUNT_SERVICE", cast=str, default="demo")
DEMO_ACCOUNT_PASSWORD = config("DEMO_ACCOUNT_PASSWORD", cast=Secret, default="demo")
SQLALCHEMY_DATABASE_URL = config(
    "SQLALCHEMY_DATABASE_URL", cast=str, default="sqlite:///./sql_app.db"
)
SQLALCHEMY_DEBUG = config("SQLALCHEMY_DEBUG", cast=bool, default=False)
# Session expiry time in seconds: 12 hours (12 * 60 * 60 = 43200)
SESSION_MAX_AGE = config("SESSION_MAX_AGE", cast=int, default=43200)
APNS_ALGORITHM = "ES256"
APNS_KEY_ID = config("APNS_KEY_ID", cast=Secret, default="key-id")
APNS_AUTH_KEY = config("APNS_AUTH_KEY", cast=Secret, default=DUMMY_PRIVATE_KEY)
TEAM_ID = config("TEAM_ID", cast=Secret, default="team")
APPLE_SERVER = config(
    "APPLE_SERVER", cast=str, default="api.development.push.apple.com"
)
BUNDLE_ID = "eu.ess.ESS-Notify"
ALLOWED_NETWORKS = config("ALLOWED_NETWORKS", cast=CommaSeparatedStrings, default="")

# Firebase settings
FIREBASE_PROJECT_ID = config("FIREBASE_PROJECT_ID", cast=str, default="my-project")
GOOGLE_APPLICATION_CREDENTIALS = config(
    "GOOGLE_APPLICATION_CREDENTIALS", cast=str, default="test-key.json"
)

# Secret key to generate jwt and encode cookies. To change in production!
SECRET_KEY = config(
    "SECRET_KEY",
    cast=Secret,
    default="3d90a5301ef713659cc1a0e33cbc87d6af55e4159d2548bae7b68c70ed133da0",
)
JWT_ALGORITHM = "HS256"
# Default token expiration time: 30 days (24 * 60 * 30 = 43200)
ACCESS_TOKEN_EXPIRE_MINUTES = config(
    "ACCESS_TOKEN_EXPIRE_MINUTES", cast=int, default=43200
)

# Number of push notifications sent in parallel
NB_PARALLEL_PUSH = config("NB_PARALLEL_PUSH", cast=int, default=50)

# Sentry Data Source Name
# Leave it empty to disable it
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")
# Environment for Sentry staging|production
ESS_NOTIFY_SERVER_ENVIRONMENT = config(
    "ESS_NOTIFY_SERVER_ENVIRONMENT", cast=str, default="staging"
)

APP_NAME = config("APP_NAME", cast=str, default="ESS Notify")

# Local timezone used for timestamp in the web app
LOCAL_TIMEZONE = config("LOCAL_TIMEZONE", cast=str, default="Europe/Stockholm")
