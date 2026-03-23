# Nebula

Simple ASGI micro framework for Python, which supports both http and websockets.

# Update changelog:
Added app.run(), mount(), render_template(), Jinja2Templates
Added new response types: PlainTextResponse, StreamingResponse, FileResponse, RedirectResponse

## Installation

```bash
pip install project-nebula
```

### Optional Dependencies

```bash
# For templates
pip install project-nebula[templates]
```

## Usage

```python
from nebula import Nebula, JSONResponse, HTMLResponse

app = Nebula()


@app.get("/")
async def home(request):
    return HTMLResponse("<h1>Welcome to Nebula!</h1>")


@app.get("/api/hello")
async def hello(request):
    return JSONResponse({"message": "Hello, World!"})


@app.post("/api/echo")
async def echo(request):
    data = await request.json()
    return JSONResponse({"echo": data})


# Typed path parameters
@app.get("/api/users/{id:int}")
async def get_user(request):
    user_id = request.path_params["id"]  # int
    return JSONResponse({"id": user_id, "name": f"User {user_id}"})


@app.get("/api/items/{name:str}")
async def get_item(request):
    name = request.path_params["name"]  # str
    return JSONResponse({"name": name, "type": "item"})


@app.get("/api/score/{value:float}")
async def get_score(request):
    value = request.path_params["value"]  # float
    return JSONResponse({"score": value, "doubled": value * 2})


# Sync handler example
@app.get("/api/sync")
def sync_handler(request):
    return JSONResponse({"type": "sync", "message": "I'm synchronous!"})


# New response types
from nebula import PlainTextResponse, StreamingResponse, FileResponse, RedirectResponse

@app.get("/text")
async def text(request):
    return PlainTextResponse("Plain text response")


@app.get("/stream")
async def stream(request):
    async def generate():
        for i in range(10):
            yield f"Line {i}\n"
    return StreamingResponse(generate())


@app.get("/download")
async def download(request):
    return FileResponse("file.pdf", filename="download.pdf")


@app.get("/redirect")
async def redirect(request):
    return RedirectResponse("https://example.com")


# Mount static files
app.mount("/static", directory="static")


# Template rendering
from nebula import Jinja2Templates
templates = Jinja2Templates(directory="templates")


@app.get("/template")
async def template(request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Home"})


# Run server directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)
```

## Run

```bash
python examples/app.py
```

Or with uvicorn directly:

```bash
uvicorn examples.app:app --reload
```

Or using app.run():

```bash
python your_app.py
```

## Features

- ASGI compliant
- JSON and HTML responses
- Path parameters support (`/users/{id}`)
- Request body parsing (JSON, text)
- Multiple HTTP methods (GET, POST, PUT, DELETE)
- Static file mounting
- Template rendering (Jinja2)
- Multiple response types (PlainText, Streaming, File, Redirect)
- Built-in server (app.run())
