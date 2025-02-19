from fastapi import APIRouter
from starlette.responses import HTMLResponse

router = APIRouter()


# Dynamic Swagger UI Route (works for `/api/v1/docs` and `/api/v2/docs`)
# Override the default Swagger UI endpoint to load some custom javascript
# and inject a bearer token
@router.get("/api/{version}/docs", include_in_schema=False)
async def custom_swagger_ui(version: str):
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <title>Notify SwaggerUI</title>
      </head>
      <body>
        <div id="swagger-ui">
        </div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="/static/js/swagger-ui-custom.js"></script>
      </body>
    </html>
    """
    return HTMLResponse(html)
