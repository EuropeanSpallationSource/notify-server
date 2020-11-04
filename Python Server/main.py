import json
import jwt
import ldap3
import secrets
import os
import time
import httpx
from fastapi import FastAPI

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
    for server in APPLE_SERVER:
        path = "/3/device/{0}".format(apn)
        with httpx.Client(http2=True) as client:
            client.post(
                "https://" + server + path, data=message, headers=request_headers
            )


def addUser(userData):
    if userData["ESSUser"] not in users:
        users[userData["ESSUser"]] = {}
    if "APNToken" not in users[userData["ESSUser"]]:
        users[userData["ESSUser"]]["APNToken"] = []
    users[userData["ESSUser"]]["ESSToken"] = userData["ESSToken"]
    if userData["APNToken"] not in users[userData["ESSUser"]]["APNToken"]:
        users[userData["ESSUser"]]["APNToken"].append(userData["APNToken"])
    saveObj(users, usersFile)
    createUserFolder(userData)


def createUserFolder(userData):
    if not os.path.isdir(userBaseDir):
        os.mkdir(userBaseDir)
    if not os.path.isdir(userBaseDir + "/" + userData["ESSUser"]):
        os.mkdir(userBaseDir + "/" + userData["ESSUser"])
    if not os.path.isfile(
        userBaseDir + "/" + userData["ESSUser"] + "/notifications.json"
    ):
        emptydata = {userData["ESSUser"]: []}
        saveObj(
            emptydata, f"{userBaseDir}/{userData['ESSUser']}/notifications.json",
        )
    if not os.path.isfile(userBaseDir + "/" + userData["ESSUser"] + "/services.json"):
        services = loadObj(servicesFile)
        emptydata = {"services": []}
        for service in services["services"]:
            emptydata["services"].append(
                {
                    "id": service["id"],
                    "Category": service["Category"],
                    "Color": service["Color"],
                    "Subscribed": False,
                }
            )
        saveObj(emptydata, f"{userBaseDir}/{userData['ESSUser']}/services.json")


def regenerateServicesFiles():
    userData = loadObj(usersFile)
    servicesData = loadObj(servicesFile)
    if not os.path.isdir(userBaseDir):
        os.mkdir(userBaseDir)
    for user in userData:
        if not os.path.isdir(userBaseDir + "/" + user):
            os.mkdir(userBaseDir + "/" + user)
        emptydata = {"services": []}
        for service in servicesData["services"]:
            emptydata["services"].append(
                {
                    "id": service["id"],
                    "Category": service["Category"],
                    "Color": service["Color"],
                    "Subscribed": user in service["Subscribers"],
                }
            )

        saveObj(emptydata, userBaseDir + "/" + user + "/services.json")


regenerateServicesFiles()


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
    serviceslist = loadObj(servicesFile)
    userservices = {"services": []}
    for service in serversData["services"]:
        userservices["services"].append(service)
        if service["Subscribed"] and (
            serversData["user"]
            not in serviceslist["services"][service["id"]]["Subscribers"]
        ):
            serviceslist["services"][service["id"]]["Subscribers"].append(
                serversData["user"]
            )
        if not service["Subscribed"] and (
            serversData["user"]
            in serviceslist["services"][service["id"]]["Subscribers"]
        ):
            serviceslist["services"][service["id"]]["Subscribers"].remove(
                serversData["user"]
            )

    saveObj(
        userservices, userBaseDir + "/" + serversData["user"] + "/services.json",
    )
    saveObj(serviceslist, servicesFile)
    return {}


@app.post("/updatenotifications")
def updateNotifications_handler(updateNotificationsData: dict):
    for i in range(len(updateNotificationsData["notifications"])):
        updateNotificationsData["notifications"][i]["id"] = i
    saveObj(
        {updateNotificationsData["user"]: updateNotificationsData["notifications"]},
        userBaseDir + "/" + updateNotificationsData["user"] + "/notifications.json",
    )
    return {}


@app.post("/newpush")
def newpush_handler(pushData: dict):
    usersData = loadObj(usersFile)
    services = loadObj(servicesFile)["services"]

    token = list(pushData.keys())[0]
    receivers = []
    usersrecv = []
    for service in services:
        if service["token"] == token:
            color = service["Color"]
            for receiver in service["Subscribers"]:
                usersrecv.append(receiver)
                for APN in usersData[receiver]["APNToken"]:
                    receivers.append(APN)

    try:
        for user in usersrecv:
            notifications = loadObj(userBaseDir + "/" + user + "/notifications.json")
            if len(notifications[user]) == 0:
                msgid = 0
            else:
                msgid = notifications[user][-1]["id"] + 1
            notifications[user].append(
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
            saveObj(notifications, userBaseDir + "/" + user + "/notifications.json")
    except Exception:
        return "Malformed Data"

    current_badge = 0
    try:
        for i in notifications[user]:
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
