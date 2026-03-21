from nebula import Nebula , HTMLResponse, Middleware, BaseMiddleware
import time

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)

        print(f"[LOG] {scope['type']} {scope.get('path')}")
        await self.app(scope, receive, send)
        print(f"[LOG END] {scope.get('path')}")


class TimingMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)

        start = time.time()
        await self.app(scope, receive, send)
        print(f"[TIME] {scope.get('path')} took {time.time() - start:.4f}s")

app: Nebula = Nebula(middleware=[
    Middleware(LoggingMiddleware),
    Middleware(TimingMiddleware)
])

@app.get("/")
async def root(request):
    return HTMLResponse("<h1>Hello, world!</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)