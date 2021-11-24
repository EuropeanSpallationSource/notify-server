from pathlib import Path
from starlette.templating import Jinja2Templates

app_dir = Path(__file__).parents[1].resolve()
templates = Jinja2Templates(directory=str(app_dir / "templates"))
