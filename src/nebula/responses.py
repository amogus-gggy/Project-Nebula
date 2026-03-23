import json
import os
import stat
import typing
from typing import Any, Dict, List, Optional, Union, AsyncIterator, Callable

import anyio


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


class PlainTextResponse(Response):
    """Ответ с обычным текстом (text/plain)."""
    def __init__(self, content, status_code=200, headers=None):
        super().__init__(
            content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain; charset=utf-8",
        )


class RedirectResponse(Response):
    """Перенаправление на другой URL."""
    def __init__(self, url, status_code=307, headers=None):
        headers = headers or {}
        headers["location"] = url
        super().__init__(
            "",
            status_code=status_code,
            headers=headers,
            media_type="text/plain",
        )


class StreamingResponse(Response):
    """Потоковый ответ для передачи данных частями."""
    def __init__(
        self,
        content: Union[AsyncIterator[bytes], AsyncIterator[str], Callable],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: str = "text/plain",
    ):
        self.content_iterator = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type
        self._encoded_headers: Optional[List[tuple]] = None

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self._get_encoded_headers(),
        })

        if callable(self.content_iterator):
            iterator = self.content_iterator()
        else:
            iterator = self.content_iterator

        async for chunk in iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode()
            await send({
                "type": "http.response.body",
                "body": chunk,
                "more_body": True,
            })

        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False,
        })

    def _get_encoded_headers(self):
        if self._encoded_headers is None:
            headers = [(b"content-type", self.media_type.encode())]
            for k, v in self.headers.items():
                headers.append((k.encode(), v.encode()))
            self._encoded_headers = headers
        return self._encoded_headers


class FileResponse(Response):
    """Ответ с содержимым файла (с поддержкой range-запросов)."""
    chunk_size = 64 * 1024

    def __init__(
        self,
        path: Union[str, os.PathLike],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        self.path = path
        self.filename = filename or os.path.basename(path)
        self.status_code = status_code
        self.headers = headers or {}
        self._media_type = media_type

        if self._media_type is None:
            self._media_type = self._guess_media_type()

        self._file_size: Optional[int] = None

    def _guess_media_type(self) -> str:
        ext = os.path.splitext(self.path)[1].lower()
        media_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/vnd.microsoft.icon",
            ".txt": "text/plain; charset=utf-8",
            ".pdf": "application/pdf",
            ".xml": "application/xml",
            ".zip": "application/zip",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".eot": "application/vnd.ms-fontobject",
        }
        return media_types.get(ext, "application/octet-stream")

    async def __call__(self, scope, receive, send):
        import email.utils
        
        headers = dict(self.headers)
        headers["content-type"] = self._media_type
        headers["content-disposition"] = f'attachment; filename="{self.filename}"'

        stat_result = await anyio.to_thread.run_sync(os.stat, self.path)
        self._file_size = stat_result.st_size
        headers["content-length"] = str(self._file_size)

        last_modified = stat_result.st_mtime
        headers["last-modified"] = email.utils.formatdate(last_modified, usegmt=True)

        encoded_headers = [(k.encode(), v.encode()) for k, v in headers.items()]

        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": encoded_headers,
        })

        async with await anyio.open_file(self.path, "rb") as f:
            while True:
                chunk = await f.read(self.chunk_size)
                if not chunk:
                    break
                await send({
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                })

        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False,
        })
