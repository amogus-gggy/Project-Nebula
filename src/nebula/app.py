import asyncio
import inspect
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from .router import Router
from .ws import WebSocket
from .request import Request
from .responses import JSONResponse, FileResponse, PlainTextResponse
from .middleware import Middleware, ASGIApp

_sync_executor = ThreadPoolExecutor(max_workers=4)

# Кэшированные 404 и 500 ответы для уменьшения аллокаций
_NOT_FOUND_RESPONSE = JSONResponse({"error": "Not Found"}, 404)
_ERROR_RESPONSE = JSONResponse({"error": "Internal Server Error"}, 500)


class Nebula:
    def __init__(self, middleware: List[Middleware] = None):
        self._router = Router()
        self._middlewares = middleware or []
        self._mounted_apps: Dict[str, Any] = {}
        self._static_dirs: Dict[str, str] = {}

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

    def mount(self, path: str, app: Any = None, directory: Union[str, os.PathLike] = None):
        """
        Подключить внешнее ASGI-приложение или директорию со статическими файлами.

        Args:
            path: Префикс пути (например, "/static" или "/api")
            app: ASGI-приложение для монтирования
            directory: Путь к директории со статическими файлами
        """
        if app is not None:
            self._mounted_apps[path] = app
        elif directory is not None:
            self._static_dirs[path] = str(directory)

    def run(self, host: str = "0.0.0.0", port: int = 8000, gc_optimize=True):
        """
        Запустить сервер uvicorn.

        Args:
            host: Хост для прослушивания
            port: Порт для прослушивания
            gc_optimize: оптимизировать ли garbage collector
        """

        if gc_optimize:
            import gc
            gc.collect(2)
            gc.freeze()
            allocs, gen1, gen2 = gc.get_threshold()
            print(allocs, gen1, gen2)
            allocs = 50000
            gen1 = gen1 * 2
            gen2 = gen2 * 2
            gc.set_threshold(allocs, gen1, gen2)
        import uvicorn
        uvicorn.run(self, host=host, port=port, http="httptools", access_log=False)

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

        # Проверка смонтированных приложений
        for mount_path, mounted_app in self._mounted_apps.items():
            if path.startswith(mount_path):
                new_scope = dict(scope)  # shallow copy to avoid mutation
                new_scope["path"] = path[len(mount_path):] or "/"
                return await mounted_app(new_scope, receive, send)

        # Проверка статических директорий
        for mount_path, directory in self._static_dirs.items():
            if path.startswith(mount_path):
                relative_path = path[len(mount_path):].lstrip("/")
                file_path = os.path.join(directory, relative_path)

                # Защита от выхода за пределы директории (используем realpath для разрешения symlink)
                abs_directory = os.path.realpath(directory)
                abs_file = os.path.realpath(file_path)

                if abs_file.startswith(abs_directory) and os.path.isfile(abs_file):
                    response = FileResponse(file_path)
                    return await response(scope, receive, send)
                else:
                    return await _NOT_FOUND_RESPONSE(scope, receive, send)

        handler, params = self._router.find_handler(path, method)

        if not handler:
            return await _NOT_FOUND_RESPONSE(scope, receive, send)

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
            await _ERROR_RESPONSE(scope, receive, send)

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
