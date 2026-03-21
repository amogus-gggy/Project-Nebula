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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
