# Nebula

Simple ASGI micro framework for Python.

## Installation

```bash
pip install -e .
```

## Usage

```python
from nebula import Nebula, JSONResponse, HTMLResponse

app = Nebula()


@app.get("/")
async def home(request):
    return HTMLResponse("<h1>Hello!</h1>")


@app.get("/api/data")
async def get_data(request):
    return JSONResponse({"key": "value"})


@app.post("/api/submit")
async def submit(request):
    data = await request.json()
    return JSONResponse({"received": data})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Run

```bash
python examples/app.py
```

Or with uvicorn directly:

```bash
uvicorn examples.app:app --reload
```

## Features

- ASGI compliant
- JSON and HTML responses
- Path parameters support (`/users/{id}`)
- Request body parsing (JSON, text)
- Multiple HTTP methods (GET, POST, PUT, DELETE)
