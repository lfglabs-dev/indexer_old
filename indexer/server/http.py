from aiohttp import web
import aiohttp_cors


class WebServer:
    def __init__(self, database) -> None:
        self.database = database

    async def fetch_tokens(self, request):
        try:
            addr = request.rel_url.query["address"]
            return web.json_response({"tokens": str(self.database[addr])})
        except Exception:
            return web.json_response({"tokens": []})

    def build_app(self):
        app = web.Application()
        app.add_routes([web.get("/fetch_tokens", self.fetch_tokens)])
        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                )
            },
        )
        for route in list(app.router.routes()):
            cors.add(route)
        return app
