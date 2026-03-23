import json
from typing import Any, Dict, List, Optional


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
