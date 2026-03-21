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


# WebSocket echo endpoint
@app.websocket("/ws/echo")
async def websocket_echo(ws: WebSocket):
    await ws.accept()
    while True:
        text = await ws.receive_text()
        print(text)
        await ws.send_text(f"Echo: {text}")


# WebSocket broadcast endpoint with room parameter
@app.websocket("/ws/chat/{room:str}")
async def websocket_chat(ws: WebSocket):
    room = ws.path_params["room"]
    await ws.accept()
    await ws.send_text(f"Welcome to room: {room}!")

    try:
        async for message in ws:
            if "text" in message:
                # Broadcast back with room info
                await ws.send_text(f"[{room}] {message['text']}")
    except Exception:
        await ws.close()


# WebSocket JSON endpoint
@app.websocket("/ws/json")
async def websocket_json(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_json()
        # Process and echo back with timestamp
        await ws.send_json({"received": data, "status": "processed"})


# Simple WebSocket Chat with broadcast
active_connections: set[WebSocket] = set()


@app.get("/chat")
async def chat_page(request):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Chat</title>
        <style>
            body { font-family: Arial; max-width: 600px; margin: 50px auto; }
            #messages { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin-bottom: 10px; }
            .message { margin: 5px 0; }
            .system { color: #888; font-style: italic; }
            input { width: 70%; padding: 8px; }
            button { padding: 8px 16px; }
        </style>
    </head>
    <body>
        <h1>💬 WebSocket Chat</h1>
        <div id="messages"></div>
        <input type="text" id="messageInput" placeholder="Type a message...">
        <button onclick="sendMessage()">Send</button>
        <script>
            const ws = new WebSocket("ws://" + location.host + "/ws/chat");
            const messages = document.getElementById("messages");
            const input = document.getElementById("messageInput");
            
            ws.onopen = () => {
                messages.innerHTML += '<div class="system">Connected to chat!</div>';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const div = document.createElement("div");
                div.className = "message";
                if (data.type === "system") {
                    div.className += " system";
                }
                div.textContent = data.username + ": " + data.message;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            };
            
            ws.onclose = () => {
                messages.innerHTML += '<div class="system">Disconnected from chat</div>';
            };
            
            function sendMessage() {
                const text = input.value.trim();
                if (text) {
                    ws.send(JSON.stringify({ message: text }));
                    input.value = "";
                }
            }
            
            input.addEventListener("keypress", (e) => {
                if (e.key === "Enter") sendMessage();
            });
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws/chat")
async def websocket_chat_broadcast(ws: WebSocket):
    await ws.accept()
    active_connections.add(ws)
    print(f"[WS] Client connected. Total connections: {len(active_connections)}")

    # Notify everyone about new user
    await broadcast(
        {
            "type": "system",
            "username": "System",
            "message": f"New user connected! Total users: {len(active_connections)}",
        }
    )

    try:
        while True:
            message = await ws.receive_json()
            print(f"[WS] Received message: {message}")
            if isinstance(message, dict) and "message" in message:
                # Broadcast message to all connections (including sender)
                await broadcast(
                    {"type": "chat", "username": "User", "message": message["message"]}
                )
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        active_connections.discard(ws)
        print(f"[WS] Client disconnected. Total connections: {len(active_connections)}")
        # Notify everyone about user disconnect
        if active_connections:
            await broadcast(
                {
                    "type": "system",
                    "username": "System",
                    "message": f"User disconnected. Total users: {len(active_connections)}",
                }
            )


async def broadcast(data: dict):
    """Broadcast message to all connected clients"""
    import json

    message = json.dumps(data)
    disconnected = set()

    print(f"[WS] Broadcasting to {len(active_connections)} connections: {data}")

    for conn in active_connections:
        try:
            await conn.send_text(message)
        except Exception as e:
            print(f"[WS] Failed to send to connection: {e}")
            disconnected.add(conn)

    # Clean up disconnected clients
    for conn in disconnected:
        active_connections.discard(conn)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
