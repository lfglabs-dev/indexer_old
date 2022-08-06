from aiohttp import web
import aiohttp_cors


class WebServer:
    def __init__(self, owners_db, verified_db) -> None:
        self.owners_db = owners_db
        self.verified_db = verified_db

    async def fetch_tokens(self, request):
        try:
            addr = request.rel_url.query["address"]
            return web.json_response({"tokens": self.owners_db[addr]})
        except Exception:
            return web.json_response({"tokens": []})

    async def reverse_lookup(self, request):
        try:
            type = request.rel_url.query["type"]
            data = request.rel_url.query["data"]
            verifier = request.rel_url.query["verifier"]
            key = str(type) + ":" + str(data) + ":" + str(verifier)
            return web.json_response({"token_id": str(self.verified_db[key])})
        except Exception:
            return web.json_response({"error": "no token found"})

    async def uri(self, request):
        try:
            id = request.rel_url.query["id"]
            return web.json_response(
                {
                    "name": f"Starknet ID: {id}",
                    "description": "This token represents an identity on StarkNet that can be linked to external services.",
                    "image": f"https://robohash.org/{id}",
                }
            )
        except Exception:
            return web.json_response({"error": "no id specified"})

    def build_app(self):
        app = web.Application()
        app.add_routes([web.get("/fetch_tokens", self.fetch_tokens)])
        app.add_routes([web.get("/reverse_lookup", self.reverse_lookup)])
        app.add_routes([web.get("/uri", self.uri)])

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
