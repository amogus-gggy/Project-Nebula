# Nebula Documentation

**Nebula** is a simple and lightweight ASGI micro-framework for Python with WebSocket support.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [Nebula](#nebula)
  - [Request](#request)
  - [Response](#response)
    - [JSONResponse](#jsonresponse)
    - [HTMLResponse](#htmlresponse)
    - [PlainTextResponse](#plaintextresponse)
    - [StreamingResponse](#streamingresponse)
    - [FileResponse](#fileresponse)
    - [RedirectResponse](#redirectresponse)
  - [WebSocket](#websocket)
- [Routing](#routing)
- [WebSocket](#websocket-1)
- [Middleware](#middleware)
- [Mounting Static Files and Applications](#mounting-static-files-and-applications)
- [Template Rendering](#template-rendering)
- [Running the Server](#running-the-server)
- [Examples](#examples)
- [Testing](#testing)
- [Development](#development)

---

## Features

- ✅ ASGI compliant
- ✅ JSON and HTML responses
- ✅ Typed path parameters (`{id:int}`, `{name:str}`, `{value:float}`)
- ✅ Request body parsing (JSON, text)
- ✅ Multiple HTTP methods (GET, POST, PUT, DELETE)
- ✅ Sync and async handlers
- ✅ Full WebSocket support
- ✅ Optimized Cython router
- ✅ Static file mounting
- ✅ Template rendering (Jinja2)
- ✅ Multiple response types (Streaming, File, Redirect, PlainText)
- ✅ Built-in `app.run()` server

---

## Installation

```bash
pip install project-nebula
```

### Requirements

- Python >= 3.10
- uvicorn >= 0.30.0
- anyio >= 4.0.0
- jinja2
### For Development

```bash
pip install project-nebula[dev]
```

Installs additional dependencies:
- pytest >= 8.0.0
- httpx >= 0.27.0
- cython >= 3.0.0



---

## Quick Start

### Minimal Application

```python
from nebula import Nebula, JSONResponse

app = Nebula()


@app.get("/")
async def home(request):
    return JSONResponse({"message": "Hello, World!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### Running

```bash
# Via main block
python examples/app.py

# Or via uvicorn
uvicorn examples.app:app --reload
```

---

## API Reference

### Nebula

Main application class.

```python
from nebula import Nebula

app = Nebula(templates_directory="templates")
```

#### Constructor Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `middleware` | `List[Middleware]` | List of middleware | `[]` |
| `templates_directory` | `str` | Directory for Jinja2 templates | `"templates"` |
| `static_directory` | `str` | Directory for static files (mounted at `/static`) | `None` |

#### Decorator Methods

| Method | Description |
|--------|-------------|
| `@app.get(path)` | Register GET route |
| `@app.post(path)` | Register POST route |
| `@app.put(path)` | Register PUT route |
| `@app.delete(path)` | Register DELETE route |
| `@app.websocket(path)` | Register WebSocket route |
| `@app.route(path, methods)` | Universal decorator |

---

### Request

HTTP request object passed to handlers.

```python
@app.get("/users/{id:int}")
async def get_user(request: Request):
    ...
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `method` | `str` | HTTP method (GET, POST, etc.) |
| `path` | `str` | Request path |
| `query_string` | `str` | Query parameters |
| `headers` | `Dict[str, str]` | Request headers |
| `path_params` | `Dict[str, Any]` | Path parameters |

#### Methods

| Method | Description |
|--------|-------------|
| `async json()` | Parse request body as JSON |
| `async text()` | Get request body as text |

---

### Response

Base HTTP response class.

```python
from nebula import Response, JSONResponse, HTMLResponse
```

#### JSONResponse

```python
@app.get("/api/data")
async def get_data(request):
    return JSONResponse({"key": "value"}, status_code=200)
```

**Parameters:**
- `content` — data to serialize to JSON
- `status_code` — status code (default 200)
- `headers` — headers (optional)

#### HTMLResponse

```python
@app.get("/")
async def home(request):
    return HTMLResponse("<h1>Welcome!</h1>")
```

**Parameters:**
- `content` — HTML content
- `status_code` — status code (default 200)
- `headers` — headers (optional)

#### PlainTextResponse

```python
from nebula import PlainTextResponse

@app.get("/text")
async def text(request):
    return PlainTextResponse("Hello, World!")
```

#### StreamingResponse

```python
from nebula import StreamingResponse

@app.get("/stream")
async def stream(request):
    async def generate():
        for i in range(10):
            yield f"Line {i}\n"
    return StreamingResponse(generate())
```

#### FileResponse

```python
from nebula import FileResponse

@app.get("/download")
async def download(request):
    return FileResponse("path/to/file.pdf", filename="myfile.pdf")
```

#### RedirectResponse

```python
from nebula import RedirectResponse

@app.get("/redirect")
async def redirect(request):
    return RedirectResponse("https://example.com")
```

---

### WebSocket

WebSocket connection handler.

```python
from nebula import WebSocket

@app.websocket("/ws/echo")
async def echo(ws: WebSocket):
    await ws.accept()
    while True:
        text = await ws.receive_text()
        await ws.send_text(f"Echo: {text}")
```

#### Methods

| Method | Description |
|--------|-------------|
| `async accept()` | Accept connection |
| `async send_text(data)` | Send text message |
| `async send_bytes(data)` | Send binary data |
| `async send_json(data)` | Send JSON |
| `async receive_text()` | Receive text |
| `async receive_bytes()` | Receive binary data |
| `async receive_json()` | Receive JSON |
| `async close(code, reason)` | Close connection |

#### States

```python
from nebula import WebSocketState

# WebSocketState.CONNECTING — connection establishing
# WebSocketState.CONNECTED — connection active
# WebSocketState.DISCONNECTED — connection closed
```

---

## Routing

### Basic Routes

```python
@app.get("/")
async def home(request):
    return HTMLResponse("<h1>Home</h1>")

@app.post("/api/users")
async def create_user(request):
    data = await request.json()
    return JSONResponse({"id": 1, **data})
```

### Typed Path Parameters

Nebula supports automatic type conversion for path parameters:

```python
# int parameter
@app.get("/api/users/{id:int}")
async def get_user(request):
    user_id = request.path_params["id"]  # int
    return JSONResponse({"id": user_id})

# str parameter
@app.get("/api/items/{name:str}")
async def get_item(request):
    name = request.path_params["name"]  # str
    return JSONResponse({"name": name})

# float parameter
@app.get("/api/score/{value:float}")
async def get_score(request):
    value = request.path_params["value"]  # float
    return JSONResponse({"score": value})
```

### Synchronous Handlers

```python
@app.get("/api/sync")
def sync_handler(request):
    return JSONResponse({"type": "sync"})
```

---

## WebSocket

### Basic Example

```python
@app.websocket("/ws/echo")
async def websocket_echo(ws: WebSocket):
    await ws.accept()
    while True:
        text = await ws.receive_text()
        await ws.send_text(f"Echo: {text}")
```

### WebSocket with Path Parameters

```python
@app.websocket("/ws/chat/{room:str}")
async def websocket_chat(ws: WebSocket):
    room = ws.path_params["room"]
    await ws.accept()
    await ws.send_text(f"Welcome to room: {room}!")
```

### Iterating Over Messages

```python
@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    async for message in ws:
        if "text" in message:
            await ws.send_text(message["text"])
```

### JSON Handling

```python
@app.websocket("/ws/json")
async def websocket_json(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_json()
        await ws.send_json({"received": data, "status": "ok"})
```

---

## Middleware

Nebula has middleware support:

```python
class Middleware:
    def __init__(self, middleware_cls: type, **options):
        self.middleware_cls = middleware_cls
        self.options = options

    def build(self, app):
        return self.middleware_cls(app, **self.options)
```

where `self.middleware_cls` is a class which inherits from BaseMiddleware:

```python
class BaseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
```

example middleware:

```python
class TimingMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)

        start = time.time()
        await self.app(scope, receive, send)
        print(f"[TIME] {scope.get('path')} took {time.time() - start:.4f}s")
```

to use it:

```python
app: Nebula = Nebula(middleware=[
    Middleware(TimingMiddleware)
])
```

---

## Mounting Static Files and Applications

### Automatic Static Files (Recommended)

You can specify a static directory when creating the application. Files will be automatically served at `/static`:

```python
from nebula import Nebula

app = Nebula(static_directory="static")

# Files are automatically served at /static/<filepath>
# e.g., /static/css/style.css, /static/js/app.js
```

### Manual Mount Static Directory

```python
from nebula import Nebula

app = Nebula()

# Mount static files manually
app.mount("/static", directory="static")

# Files are served at /static/<filepath>
# e.g., /static/css/style.css, /static/js/app.js
```

### Mount ASGI Application

```python
from nebula import Nebula

app = Nebula()

# Mount another ASGI app
from some_module import sub_app
app.mount("/api", app=sub_app)
```

---

## Template Rendering

Nebula supports Jinja2 templates for rendering HTML.

### Configuring Templates Directory

You can specify the templates directory when creating the application:

```python
from nebula import Nebula

app = Nebula(templates_directory="templates")
```

### Using Jinja2Templates (Recommended)

```python
from nebula import Nebula, Jinja2Templates

app = Nebula(templates_directory="templates")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Home Page", "user": "John"}
    )
```

### Using render_template Function

```python
from nebula import Nebula, render_template

app = Nebula(templates_directory="templates")


@app.get("/")
async def home(request):
    return render_template(
        "index.html",
        {"title": "Home", "user": "John"}
    )
```

### Template Example (templates/index.html)

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>Hello, {{ user }}!</h1>
</body>
</html>
```

**Note:** Install Jinja2 with `pip install jinja2` or `pip install project-nebula[templates]`

---

## Running the Server

### Using app.run()

```python
from nebula import Nebula

app = Nebula()


@app.get("/")
async def home(request):
    return HTMLResponse("<h1>Hello!</h1>")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)
```

### Parameters

- `host` — Host to bind (default: "127.0.0.1")
- `port` — Port to bind (default: 8000)
- `reload` — Auto-reload on code changes (default: False)
- `**kwargs` — Additional uvicorn.run() arguments

---

## Examples

### Full Application

```python
from nebula import Nebula, JSONResponse, HTMLResponse, WebSocket

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


@app.websocket("/ws/echo")
async def websocket_echo(ws: WebSocket):
    await ws.accept()
    while True:
        text = await ws.receive_text()
        await ws.send_text(f"Echo: {text}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

More examples available in `examples/` folder.

---

## Testing

### Running Tests

```bash
# Make sure server is running on port 8000
python examples/app.py &

# Run tests
python test_app.py
```

### Test Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | HTML page |
| `/api/hello` | GET | JSON response |
| `/api/echo` | POST | Echo JSON |
| `/api/users/{id:int}` | GET | int parameter |
| `/api/items/{name:str}` | GET | str parameter |
| `/api/score/{value:float}` | GET | float parameter |
| `/api/sync` | GET | Sync handler |
| `/ws/echo` | WS | Echo WebSocket |
| `/ws/chat/{room:str}` | WS | Chat with room |
| `/ws/json` | WS | JSON WebSocket |

---

## Development

### Project Structure

```
Project-Nebula/
├── src/
│   └── nebula/
│       ├── __init__.py
│       ├── app.py        # Main application
│       ├── router.pyx    # Cython router
│       └── ws.py         # WebSocket support
├── examples/
│   └── app.py            # Usage examples
|   └── basic.py
├── test_app.py           # Tests
├── pyproject.toml        # Build configuration
└── setup.py              # Setup script
```

### Building

```bash
pip install -e .[dev]
```

### Dependencies

**Core:**
- uvicorn >= 0.30.0

**Development:**
- pytest >= 8.0.0
- httpx >= 0.27.0
- cython >= 3.0.0

---

## License

AGPLv3 License — see `LICENSE.txt` for details.

---

## Links

- [GitHub Repository](https://github.com/amogus-gggy/project-nebula)
- [PyPI Package](https://pypi.org/project/project-nebula/)
