import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from .router import Router
from .ws import WebSocket
from .request import Request
from .responses import JSONResponse
from .middleware import Middleware, ASGIApp

_sync_executor = ThreadPoolExecutor(max_workers=10)


class Nebula:
    def __init__(self, middleware: List[Middleware] = None):
        self._router = Router()
        self._middlewares = middleware or []

        self._core = self._build_core()
        self._app = self._build_middlewares(self._core)
        self._sync_executor = _sync_executor

    def route(self, path, methods=None):
        methods = methods or ["GET"]

        def decorator(func):
            for m in methods:
                self._router.add_route(path, m.upper(), func)
            return func

        return decorator

    def get(self, path):
        return self.route(path, ["GET"])

    def post(self, path):
        return self.route(path, ["POST"])

    def put(self, path):
        return self.route(path, ["PUT"])

    def delete(self, path):
        return self.route(path, ["DELETE"])

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
                    self._sync_executor,
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
                await asyncio.get_running_loop().run_in_executor(
                    self._sync_executor,
                    handler,
                    websocket,
                )

        except Exception as e:
            try:
                await websocket.close(1011, str(e))
            except Exception:
                pass

    async def __call__(self, scope, receive, send):
        return await self._app(scope, receive, send)
