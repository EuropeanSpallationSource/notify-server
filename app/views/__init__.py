from pathlib import Path
from zoneinfo import ZoneInfo
from starlette.templating import Jinja2Templates
from ..settings import LOCAL_TIMEZONE

app_dir = Path(__file__).parents[1].resolve()
templates = Jinja2Templates(directory=str(app_dir / "templates"))


def format_datetime(dt):
    return dt.astimezone(ZoneInfo(LOCAL_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


templates.env.filters["format_datetime"] = format_datetime
