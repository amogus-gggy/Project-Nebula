import asyncio
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Dict, List, Optional

from .router import Router


# Thread pool for sync handlers - shared instance for efficiency
_sync_executor = ThreadPoolExecutor(max_workers=10)


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
        self.headers = {
            k.decode(): v.decode() for k, v in scope.get("headers", [])
        }
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

    async def __call__(
        self,
        scope: Dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] != "http":
            return

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
                response = JSONResponse(
                    {"error": str(e)}, status_code=500
                )
                await response(scope, receive, send)
        else:
            response = JSONResponse({"error": "Not Found"}, status_code=404)
            await response(scope, receive, send)
