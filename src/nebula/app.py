import asyncio
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Callable, Any, Dict, List, Optional, Iterable

from .router import Router


# Thread pool for sync handlers - shared instance for efficiency
_sync_executor = ThreadPoolExecutor(max_workers=10)


class WebSocketState(Enum):
    """WebSocket connection state."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class Request:
    """HTTP request object."""

    def __init__(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        path_params: Optional[Dict[str, Any]] = None,
    ):
        self.scope = scope
        self.receive = receive
        self.method = scope.get("method", "GET")
        self.path = scope.get("path", "/")
        self.query_string = scope.get("query_string", b"").decode()
        self.headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        self.path_params = path_params or {}

    async def json(self) -> Dict[str, Any]:
        """Parse request body as JSON."""
        body = await self._get_body()
        return json.loads(body)

    async def text(self) -> str:
        """Get request body as text."""
        return await self._get_body()

    async def _get_body(self) -> str:
        """Read request body."""
        messages = []
        while True:
            message = await self.receive()
            messages.append(message)
            if not message.get("more_body", False):
                break
        return b"".join(msg.get("body", b"") for msg in messages).decode()


class Response:
    """Base HTTP response."""

    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: str = "text/plain",
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type

    async def __call__(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self._encode_headers(),
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": self._encode_content(),
            }
        )

    def _encode_headers(self) -> List[tuple]:
        headers = [(b"content-type", self.media_type.encode())]
        for key, value in self.headers.items():
            headers.append((key.encode(), value.encode()))
        return headers

    def _encode_content(self) -> bytes:
        if isinstance(self.content, str):
            return self.content.encode()
        return self.content


def _run_sync_handler(handler: Callable, request: Request) -> Any:
    """Run synchronous handler in thread pool."""
    return handler(request)


class JSONResponse(Response):
    """JSON response."""

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=json.dumps(content),
            status_code=status_code,
            headers=headers,
            media_type="application/json",
        )


class HTMLResponse(Response):
    """HTML response."""

    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/html; charset=utf-8",
        )


class WebSocket:
    """WebSocket connection handler."""

    def __init__(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        send: Callable,
        path_params: Optional[Dict[str, Any]] = None,
    ):
        self.scope = scope
        self._receive = receive
        self._send = send
        self.path = scope.get("path", "/")
        self.headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        self.path_params = path_params or {}
        self._state = WebSocketState.CONNECTING

    @property
    def state(self) -> WebSocketState:
        """Get current connection state."""
        return self._state

    async def receive(self) -> Dict[str, Any]:
        """
        Receive ASGI websocket messages, ensuring valid state transitions.
        """
        if self._state == WebSocketState.CONNECTING:
            message = await self._receive()
            message_type = message["type"]
            if message_type != "websocket.connect":
                raise RuntimeError(
                    f'Expected ASGI message "websocket.connect", but got {message_type!r}'
                )
            # Stay in CONNECTING until the application explicitly accepts.
            # This mirrors Starlette/FastAPI semantics: the connect event is received,
            # but the handshake isn't complete until we send "websocket.accept".
            return message
        elif self._state == WebSocketState.CONNECTED:
            message = await self._receive()
            message_type = message["type"]
            if message_type not in {"websocket.receive", "websocket.disconnect"}:
                raise RuntimeError(
                    f'Expected ASGI message "websocket.receive" or "websocket.disconnect", but got {message_type!r}'
                )
            if message_type == "websocket.disconnect":
                self._state = WebSocketState.DISCONNECTED
            return message
        else:
            raise RuntimeError(
                'Cannot call "receive" once a disconnect message has been received.'
            )

    async def send(self, message: Dict[str, Any]) -> None:
        """
        Send ASGI websocket messages, ensuring valid state transitions.
        """
        if self._state == WebSocketState.CONNECTING:
            message_type = message["type"]
            if message_type not in {"websocket.accept", "websocket.close"}:
                raise RuntimeError(
                    f'Expected ASGI message "websocket.accept" or "websocket.close", but got {message_type!r}'
                )
            if message_type == "websocket.close":
                self._state = WebSocketState.DISCONNECTED
            else:
                self._state = WebSocketState.CONNECTED
            await self._send(message)
        elif self._state == WebSocketState.CONNECTED:
            message_type = message["type"]
            if message_type not in {"websocket.send", "websocket.close"}:
                raise RuntimeError(
                    f'Expected ASGI message "websocket.send" or "websocket.close", but got {message_type!r}'
                )
            if message_type == "websocket.close":
                self._state = WebSocketState.DISCONNECTED
            try:
                await self._send(message)
            except OSError:
                self._state = WebSocketState.DISCONNECTED
                raise RuntimeError("WebSocket disconnected")
        else:
            raise RuntimeError('Cannot call "send" once a close message has been sent.')

    async def accept(
        self,
        subprotocol: Optional[str] = None,
        headers: Optional[Iterable[tuple[bytes, bytes]]] = None,
    ) -> None:
        headers = headers or []

        if self._state == WebSocketState.CONNECTING:
            # If we haven't yet seen the 'connect' message, then wait for it first.
            await self.receive()
        await self.send(
            {"type": "websocket.accept", "subprotocol": subprotocol, "headers": headers}
        )

    def _raise_on_disconnect(self, message: Dict[str, Any]) -> None:
        if message["type"] == "websocket.disconnect":
            raise RuntimeError(
                f"WebSocket disconnected with code {message.get('code', 1000)}"
            )

    async def close(self, code: int = 1000, reason: Optional[str] = None) -> None:
        await self.send(
            {"type": "websocket.close", "code": code, "reason": reason or ""}
        )

    async def send_text(self, data: str) -> None:
        """Send text data over the WebSocket."""
        if self._state == WebSocketState.CONNECTING:
            await self.accept()
        await self.send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        """Send binary data over the WebSocket."""
        if self._state == WebSocketState.CONNECTING:
            await self.accept()
        await self.send({"type": "websocket.send", "bytes": data})

    async def send_json(self, data: Any) -> None:
        """Send JSON data over the WebSocket."""
        if self._state == WebSocketState.CONNECTING:
            await self.accept()
        await self.send_text(json.dumps(data))

    async def receive_text(self) -> str:
        """Receive text data from the WebSocket."""
        if self._state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )

        while True:
            message = await self._receive()
            if message["type"] == "websocket.disconnect":
                self._state = WebSocketState.DISCONNECTED
                raise RuntimeError(
                    f"WebSocket disconnected with code {message.get('code', 1000)}"
                )
            elif message["type"] == "websocket.receive":
                text = message.get("text")
                if text:
                    return text

                continue

    async def receive_bytes(self) -> bytes:
        if self._state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )

        while True:
            message = await self._receive()
            if message["type"] == "websocket.disconnect":
                self._state = WebSocketState.DISCONNECTED
                raise RuntimeError(
                    f"WebSocket disconnected with code {message.get('code', 1000)}"
                )
            elif message["type"] == "websocket.receive":
                data = message.get("bytes")
                if data:
                    return data
                continue

    async def receive_json(self) -> Any:
        """Receive JSON data from the WebSocket."""
        text = await self.receive_text()
        return json.loads(text)

    async def __aiter__(self):
        """Iterate over incoming messages."""
        while self._state != WebSocketState.DISCONNECTED:
            try:
                message = await self.receive()
                if message["type"] == "websocket.disconnect":
                    self._state = WebSocketState.DISCONNECTED
                    break
                if message["type"] == "websocket.receive":
                    yield message
            except Exception:
                break


class Nebula:
    """ASGI micro framework."""

    def __init__(self):
        self._router = Router()

    def route(self, path: str, methods: List[str] = None):
        """Decorator to register a route."""
        if methods is None:
            methods = ["GET"]

        def decorator(func: Callable) -> Callable:
            for method in methods:
                self._router.add_route(path, method.upper(), func)
            return func

        return decorator

    def get(self, path: str):
        """Decorator for GET route."""
        return self.route(path, methods=["GET"])

    def post(self, path: str):
        """Decorator for POST route."""
        return self.route(path, methods=["POST"])

    def put(self, path: str):
        """Decorator for PUT route."""
        return self.route(path, methods=["PUT"])

    def delete(self, path: str):
        """Decorator for DELETE route."""
        return self.route(path, methods=["DELETE"])

    def websocket(self, path: str):
        """Decorator for WebSocket route."""

        def decorator(func: Callable) -> Callable:
            self._router.add_websocket_route(path, func)
            return func

        return decorator

    async def __call__(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "/")
            method = scope.get("method", "GET")

            # Find route and extract path params using Cython router
            handler, path_params = self._router.find_handler(path, method)

            if handler:
                request = Request(scope, receive, path_params)
                try:
                    # Check if handler is sync or async
                    if inspect.iscoroutinefunction(handler):
                        response = await handler(request)
                    else:
                        # Run sync handler in thread pool
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(
                            _sync_executor, _run_sync_handler, handler, request
                        )
                    await response(scope, receive, send)
                except Exception as e:
                    response = JSONResponse({"error": str(e)}, status_code=500)
                    await response(scope, receive, send)
            else:
                response = JSONResponse({"error": "Not Found"}, status_code=404)
                await response(scope, receive, send)

        elif scope["type"] == "websocket":
            path = scope.get("path", "/")

            # Find WebSocket handler using Cython router
            handler, path_params = self._router.find_websocket_handler(path)

            if handler:
                websocket = WebSocket(scope, receive, send, path_params)
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler(websocket)
                    else:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(_sync_executor, handler, websocket)
                except Exception as e:
                    # Try to send close frame on error
                    try:
                        await websocket.close(code=1011, reason=str(e))
                    except Exception:
                        pass
