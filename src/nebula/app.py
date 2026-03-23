import asyncio
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Dict, List, Optional

from .router import Router
from .ws import WebSocket, WebSocketState

_sync_executor = ThreadPoolExecutor(max_workers=10)


class Request:
    def __init__(self, scope: Dict[str, Any], receive: Callable, path_params=None):
        self.scope = scope
        self.receive = receive
        self.method = scope.get("method", "GET")
        self.path = scope.get("path", "/")
        self.query_string = scope.get("query_string", b"").decode()
        self.headers = {
            k.decode(): v.decode()
            for k, v in scope.get("headers", [])
        }
        self.path_params = path_params or {}
        self._body: Optional[bytes] = None

    async def _get_body(self) -> bytes:
        if self._body is not None:
            return self._body

        messages = []
        while True:
            message = await self.receive()
            messages.append(message)
            if not message.get("more_body", False):
                break

        self._body = b"".join(m.get("body", b"") for m in messages)
        return self._body

    async def json(self):
        body = await self._get_body()
        return json.loads(body)

    async def text(self):
        body = await self._get_body()
        return body.decode()



class Response:
    def __init__(self, content="", status_code=200, headers=None, media_type="text/plain"):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type
        self._encoded_headers: Optional[List[tuple]] = None
        self._encoded_body: Optional[bytes] = None

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self._get_encoded_headers(),
        })

        await send({
            "type": "http.response.body",
            "body": self._get_encoded_body(),
        })

    def _get_encoded_headers(self):
        if self._encoded_headers is None:
            headers = [(b"content-type", self.media_type.encode())]
            for k, v in self.headers.items():
                headers.append((k.encode(), v.encode()))
            self._encoded_headers = headers
        return self._encoded_headers

    def _get_encoded_body(self):
        if self._encoded_body is None:
            self._encoded_body = self.content.encode() if isinstance(self.content, str) else self.content
        return self._encoded_body


class JSONResponse(Response):
    def __init__(self, content, status_code=200, headers=None):
        super().__init__(
            json.dumps(content),
            status_code=status_code,
            headers=headers,
            media_type="application/json",
        )


class HTMLResponse(Response):
    def __init__(self, content, status_code=200, headers=None):
        super().__init__(
            content,
            status_code=status_code,
            headers=headers,
            media_type="text/html; charset=utf-8",
        )



class BaseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


class Middleware:
    def __init__(self, middleware_cls: type, **options):
        self.middleware_cls = middleware_cls
        self.options = options

    def build(self, app):
        return self.middleware_cls(app, **self.options)


ASGIApp = Callable[[Dict, Callable, Callable], Any]



class Nebula:
    def __init__(self, middleware: List[Middleware] = None):
        self._router = Router()
        self._middlewares = middleware or []

        self._core = self._build_core()
        self._app = self._build_middlewares(self._core)


    def route(self, path, methods=None):
        methods = methods or ["GET"]

        def decorator(func):
            for m in methods:
                self._router.add_route(path, m.upper(), func)
            return func

        return decorator

    def get(self, path): return self.route(path, ["GET"])
    def post(self, path): return self.route(path, ["POST"])
    def put(self, path): return self.route(path, ["PUT"])
    def delete(self, path): return self.route(path, ["DELETE"])

    def websocket(self, path):
        def decorator(func):
            self._router.add_websocket_route(path, func)
            return func

        return decorator


    def _build_core(self):
        async def app(scope, receive, send):
            if scope["type"] == "http":
                return await self._handle_http(scope, receive, send)
            elif scope["type"] == "websocket":
                return await self._handle_ws(scope, receive, send)

        return app

    def _build_middlewares(self, app: ASGIApp) -> ASGIApp:
        for mw in reversed(self._middlewares):
            app = mw.build(app)
        return app

    async def _handle_http(self, scope, receive, send):
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        handler, params = self._router.find_handler(path, method)

        if not handler:
            return await JSONResponse({"error": "Not Found"}, 404)(scope, receive, send)

        request = Request(scope, receive, params)

        try:
            if inspect.iscoroutinefunction(handler):
                response = await handler(request)
            else:
                response = await asyncio.get_running_loop().run_in_executor(
                    _sync_executor,
                    handler,
                    request,
                )

            await response(scope, receive, send)
        except Exception as e:
            await JSONResponse({"error": str(e)}, 500)(scope, receive, send)

    async def _handle_ws(self, scope, receive, send):
        path = scope.get("path", "/")

        handler, params = self._router.find_websocket_handler(path)
        websocket = WebSocket(scope, receive, send, params)

        if not handler:
            await websocket.close(1000)
            return

        try:
            if inspect.iscoroutinefunction(handler):
                await handler(websocket)
            else:
                await asyncio.get_running_loop().run_in_executor(_sync_executor, handler, websocket)

        except Exception as e:
            try:
                await websocket.close(1011, str(e))
            except Exception:
                pass

    async def __call__(self, scope, receive, send):
        return await self._app(scope, receive, send)