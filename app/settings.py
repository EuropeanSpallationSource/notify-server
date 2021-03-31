from starlette.config import Config
from starlette.datastructures import Secret, CommaSeparatedStrings

DUMMY_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgtAParbMemenK/+8T
JYWanX1jzKaFcgmupVALPHyaKKKhRANCAARVmMAXI+WPS/vjIsFBHb3B5dQKqgT8
ytZPnlbWNLGGR7tKdB1eLzyBlIVFe9El4Wlvs19ACPRMtE7l75IlbOT+
-----END PRIVATE KEY-----
"""

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

# Secret key to generate jwt. To change in production!
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
