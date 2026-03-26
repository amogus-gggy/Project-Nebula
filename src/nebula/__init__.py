import warnings
from typing import Any

# Import all with underscore prefix to hide them from direct access
from .app import Nebula
from .http import Request as _Request
from .http import (
    Response as _Response,
    JSONResponse as _JSONResponse,
    HTMLResponse as _HTMLResponse,
    PlainTextResponse as _PlainTextResponse,
    StreamingResponse as _StreamingResponse,
    FileResponse as _FileResponse,
    RedirectResponse as _RedirectResponse,
)
from .middleware import BaseMiddleware as _BaseMiddleware, Middleware as _Middleware, ASGIApp as _ASGIApp
from .websocket import WebSocket as _WebSocket, WebSocketState as _WebSocketState
from .templating import (
    Jinja2Templates as _Jinja2Templates,
    TemplateResponse as _TemplateResponse,
    render_template as _render_template,
    set_default_templates_directory as _set_default_templates_directory,
    get_default_templates_directory as _get_default_templates_directory,
)
from .caching import (
    CacheBackend as _CacheBackend,
    InMemoryCache as _InMemoryCache,
    CacheManager as _CacheManager,
    CacheMiddleware as _CacheMiddleware,
    cache as _cache,
)


# Mapping of attribute names to their correct import paths and actual objects
_IMPORT_MAPPING = {
    "Request": ("nebula.http", _Request),
    "Response": ("nebula.http", _Response),
    "JSONResponse": ("nebula.http", _JSONResponse),
    "HTMLResponse": ("nebula.http", _HTMLResponse),
    "PlainTextResponse": ("nebula.http", _PlainTextResponse),
    "StreamingResponse": ("nebula.http", _StreamingResponse),
    "FileResponse": ("nebula.http", _FileResponse),
    "RedirectResponse": ("nebula.http", _RedirectResponse),
    "BaseMiddleware": ("nebula.middleware", _BaseMiddleware),
    "Middleware": ("nebula.middleware", _Middleware),
    "ASGIApp": ("nebula.middleware", _ASGIApp),
    "WebSocket": ("nebula.websocket", _WebSocket),
    "WebSocketState": ("nebula.websocket", _WebSocketState),
    "Jinja2Templates": ("nebula.templating", _Jinja2Templates),
    "TemplateResponse": ("nebula.templating", _TemplateResponse),
    "render_template": ("nebula.templating", _render_template),
    "set_default_templates_directory": ("nebula.templating", _set_default_templates_directory),
    "get_default_templates_directory": ("nebula.templating", _get_default_templates_directory),
    "CacheBackend": ("nebula.caching", _CacheBackend),
    "InMemoryCache": ("nebula.caching", _InMemoryCache),
    "CacheManager": ("nebula.caching", _CacheManager),
    "CacheMiddleware": ("nebula.caching", _CacheMiddleware),
    "cache": ("nebula.caching", _cache),
}


def __getattr__(name: str) -> Any:
    if name in _IMPORT_MAPPING:
        module_path, obj = _IMPORT_MAPPING[name]
        warnings.warn(
            f"Importing '{name}' directly from 'nebula' is deprecated. "
            f"Use 'from {module_path} import {name}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return obj
    
    if name == "__version__":
        return "0.1.0"
    
    raise AttributeError(f"module 'nebula' has no attribute '{name}'")


__all__ = [
    "Nebula",
    "Request",
    "Response",
    "JSONResponse",
    "HTMLResponse",
    "PlainTextResponse",
    "StreamingResponse",
    "FileResponse",
    "RedirectResponse",
    "WebSocket",
    "WebSocketState",
    "BaseMiddleware",
    "Middleware",
    "ASGIApp",
    "Jinja2Templates",
    "TemplateResponse",
    "render_template",
    "set_default_templates_directory",
    "get_default_templates_directory",
    "CacheBackend",
    "InMemoryCache",
    "CacheManager",
    "CacheMiddleware",
    "cache",
]
