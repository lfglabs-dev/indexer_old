from aiohttp import web
import aiohttp_cors


class WebServer:
    def __init__(self, owners_db, verified_db) -> None:
        self.owners_db = owners_db
        self.verified_db = verified_db

    async def fetch_tokens(self, request):
        try:
            addr = request.rel_url.query["address"]
            print("Fetching tokens for addr:", addr)
            return web.json_response({"tokens": self.owners_db[addr]})
        except Exception:
            return web.json_response({"tokens": []})

    async def fetch_token_id(self, request):
        print("Fetching token id")
        try:
            type = request.rel_url.query["type"]
            data = request.rel_url.query["data"]
            verifier = request.rel_url.query["verifier"]
            key = str(type) + ":" + str(data) + ":" + str(verifier)
            return web.json_response({"token_id": str(self.verified_db[key])})
        except Exception:
            return web.json_response({"error": "no token found"})

    def build_app(self):
        app = web.Application()
        app.router.add_route("GET", "/fetch_tokens", self.fetch_tokens)
        app.router.add_route("GET", "/fetch_tokens_id", self.fetch_token_id)

        # Enable CORS for all origins
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

        # Configure CORS on all routes
        for route in list(app.router.routes()):
            cors.add(route)

        return app
