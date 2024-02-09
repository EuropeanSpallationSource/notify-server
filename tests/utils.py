import datetime


def no_tz_isoformat(dt: datetime.datetime) -> str:
    """Return a datetime as string without the timezone information

    We were using naive datetime object previously (using utcnow()).
    We switch to timezone aware datetime but must continue returning
    timestamp without timezone info in json to not brake compatibility
    with current mobile clients.
    """
    return dt.isoformat().replace("+00:00", "")
