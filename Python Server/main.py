import json
import jwt
import ldap3
import secrets
import os
import time
import httpx
from typing import Optional
from fastapi import FastAPI, Header

LDAPServerName = os.environ.get("LDAP_SERVER")
LDAPServer = ldap3.Server(LDAPServerName, use_ssl=True)

usersFile = "./users.json"
servicesFile = "./services.json"
userBaseDir = os.environ.get("USER_BASE_DIR")

ALGORITHM = "ES256"
APNS_KEY_ID = os.environ.get("APNS_KEY_ID")
APNS_AUTH_KEY = os.environ.get("APNS_AUTH_KEY")
TEAM_ID = os.environ.get("TEAM_ID")
APPLE_SERVER = ["api.development.push.apple.com:443", "api.push.apple.com:443"]
BUNDLE_ID = "eu.ess.ESS-Notify"

app = FastAPI()


def saveObj(obj, filename):
    with open(filename, "w") as f:
        json.dump(obj, f)


def loadObj(filename):
    with open(filename, "r") as f:
        return json.load(f)


if os.path.isfile(usersFile):
    users = loadObj(usersFile)
else:
    users = {}


if os.path.isfile(servicesFile):
    services = loadObj(servicesFile)
else:
    print("Missing services file")
    quit()


def sendPushToDevice(apn, message):
    token = jwt.encode(
        {"iss": TEAM_ID, "iat": time.time()},
        APNS_AUTH_KEY,
        algorithm=ALGORITHM,
        headers={"alg": ALGORITHM, "kid": APNS_KEY_ID},
    )
    request_headers = {
        "apns-expiration": "0",
        "apns-priority": "10",
        "apns-topic": BUNDLE_ID,
        "authorization": "bearer {0}".format(token.decode("ascii")),
    }
    with httpx.Client(http2=True) as client:
        for server in APPLE_SERVER:
            url = f"https://{server}/3/device/{apn}"
            client.post(url, data=message, headers=request_headers)


def addUser(userData):
    if userData["ESSUser"] not in users:
        users[userData["ESSUser"]] = {}
    if "APNToken" not in users[userData["ESSUser"]]:
        users[userData["ESSUser"]]["APNToken"] = []
    if "Notifications" not in users[userData["ESSUser"]]:
        users[userData["ESSUser"]]["Notifications"] = []
    users[userData["ESSUser"]]["ESSToken"] = userData["ESSToken"]
    if userData["APNToken"] not in users[userData["ESSUser"]]["APNToken"]:
        users[userData["ESSUser"]]["APNToken"].append(userData["APNToken"])
    saveObj(users, usersFile)


@app.post("/auth")
def auth_handler(userData: dict):
    if not userData["Registered"]:
        try:
            LDAPConnection = ldap3.Connection(
                LDAPServer, userData["ESSUser"] + "@esss.se", userData["ESSToken"],
            )
            if LDAPConnection.bind():
                userData["Registered"] = True
                if userData["ESSUser"] in users:
                    userData["ESSToken"] = users[userData["ESSUser"]]["ESSToken"]
                else:
                    userData["ESSToken"] = secrets.token_hex(32)
                LDAPConnection.unbind()
                addUser(userData)
            else:
                userData["Registered"] = False
                userData["ESSToken"] = ""
        except Exception:
            None
    else:
        if (
            userData["ESSUser"] in users
            and userData["ESSToken"] == users[userData["ESSUser"]]["ESSToken"]
        ):
            userData["Registered"] = True
            addUser(userData)
        else:
            userData["Registered"] = False
    return userData


@app.post("/services")
def services_handler(serversData: dict):
    userservices = {"services": []}
    for service in serversData["services"]:
        userservices["services"].append(service)
        if service["Subscribed"] and (
            serversData["user"]
            not in services["services"][service["id"]]["Subscribers"]
        ):
            services["services"][service["id"]]["Subscribers"].append(
                serversData["user"]
            )
        if not service["Subscribed"] and (
            serversData["user"] in services["services"][service["id"]]["Subscribers"]
        ):
            services["services"][service["id"]]["Subscribers"].remove(
                serversData["user"]
            )

    saveObj(services, servicesFile)
    return {}


@app.post("/updatenotifications")
def updateNotifications_handler(updateNotificationsData: dict):
    for i in range(len(updateNotificationsData["notifications"])):
        updateNotificationsData["notifications"][i]["id"] = i

    users[updateNotificationsData["user"]]["Notifications"] = updateNotificationsData[
        "notifications"
    ]
    saveObj(users, usersFile)
    return {}


@app.post("/newpush")
def newpush_handler(pushData: dict):
    token = list(pushData.keys())[0]
    receivers = []
    usersrecv = []
    for service in services["services"]:
        if service["token"] == token:
            color = service["Color"]
            for receiver in service["Subscribers"]:
                usersrecv.append(receiver)
                for APN in users[receiver]["APNToken"]:
                    receivers.append(APN)

    try:
        for user in usersrecv:
            notifications = users[user]["Notifications"]
            if len(notifications) == 0:
                msgid = 0
            else:
                msgid = notifications[-1]["id"] + 1
            notifications.append(
                {
                    "id": msgid,
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Color": color,
                    "Title": pushData[token]["Title"],
                    "Subtitle": pushData[token]["Message"],
                    "URL": pushData[token]["url"],
                    "Read": False,
                }
            )
            users[user]["Notifications"] = notifications
            saveObj(users, usersFile)
    except Exception:
        return "Malformed Data"

    current_badge = 0
    try:
        for i in notifications:
            if not i["Read"]:
                current_badge += 1
        payload_data = {
            "aps": {
                "alert": {
                    "title": pushData[token]["Title"],
                    "subtitle": pushData[token]["Message"],
                },
                "badge": current_badge,
                "sound": "default",
            }
        }
        message = json.dumps(payload_data).encode("utf-8")
        for apn in receivers:
            sendPushToDevice(apn, message)
        return "Message Delivered"
    except Exception:
        return "Error sending message"


@app.get("/push/usersfeeds/{user}/services.json")
def services_for_user(user: str, token: Optional[str] = Header(None)):
    if user in users and users[user]["ESSToken"] == token:
        return_services = []
        for service in services["services"]:
            return_service = {}
            return_service["id"] = service["id"]
            return_service["Category"] = service["Category"]
            return_service["Color"] = service["Color"]
            if user in service["Subscribers"]:
                return_service["Subscribed"] = True
            else:
                return_service["Subscribed"] = False
            return_services.append(return_service)
        return {"services": return_services}
    else:
        return {"services": []}


@app.get("/push/usersfeeds/{user}/notifications.json")
def notifications_for_user(user: str, token: Optional[str] = Header(None)):
    if user in users and users[user]["ESSToken"] == token:
        return {user: users[user]["Notifications"]}
    else:
        return {user: []}
