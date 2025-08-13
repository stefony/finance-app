from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp
from fastapi import FastAPI

class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                headers = message.setdefault("headers", [])
                def add(k, v): headers.append((k.encode(), v.encode()))
                add("x-frame-options", "DENY")
                add("x-content-type-options", "nosniff")
                add("referrer-policy", "strict-origin-when-cross-origin")
                add("permissions-policy", "geolocation=(), microphone=(), camera=()")
                add("strict-transport-security", "max-age=63072000; includeSubDomains; preload")
            await send(message)
        await self.app(scope, receive, send_wrapper)

def harden(app: FastAPI) -> FastAPI:
    app.add_middleware(GZipMiddleware, minimum_size=512)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # смени на прод домейна по-късно
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    return app
