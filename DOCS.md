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
  - [WebSocket](#websocket)
- [Routing](#routing)
- [WebSocket](#websocket-1)
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

---

## Installation

```bash
pip install project-nebula
```

### Requirements

- Python >= 3.10
- uvicorn >= 0.30.0

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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
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

app = Nebula()
```

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
