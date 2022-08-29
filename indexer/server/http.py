from aiohttp import web
import aiohttp_cors


class WebServer:
    def __init__(
        self,
        owners_db,
        verified_db,
        domain_to_addr_db,
        addr_to_domain_db,
        tokenid_to_domain_db,
    ) -> None:
        self.owners_db = owners_db
        self.verified_db = verified_db
        self.domain_to_addr_db = domain_to_addr_db
        self.addr_to_domain_db = addr_to_domain_db
        self.tokenid_to_domain_db = tokenid_to_domain_db

    async def address_to_ids(self, request):
        try:
            addr = request.rel_url.query["address"]
            return web.json_response({"ids": self.owners_db[addr]})
        except Exception:
            return web.json_response({"ids": []})

    async def field_data_to_id(self, request):
        try:
            field = request.rel_url.query["field"]
            data = request.rel_url.query["data"]
            verifier = request.rel_url.query["verifier"]
            key = str(field) + ":" + str(data) + ":" + str(verifier)
            return web.json_response({"id": str(self.verified_db[key])})
        except Exception:
            return web.json_response({"error": "no token found"})

    async def tokenid_to_domain(self, request):
        try:
            token_id = request.rel_url.query["id"]
            domain = self.tokenid_to_domain_db["id:" + str(token_id)]
            return web.json_response({"domain": domain})
        except KeyError:
            return web.json_response({"error": "no domain found"})

    async def domain_to_addr(self, request):
        try:
            domain = request.rel_url.query["domain"]
            addr = self.domain_to_addr_db[domain]
            return web.json_response({"addr": addr})
        except KeyError:
            return web.json_response({"error": "no address found"})

    async def addr_to_domain(self, request):
        try:
            addr = request.rel_url.query["addr"]
            domain = self.addr_to_domain_db[addr]
            return web.json_response({"domain": domain})
        except KeyError:
            return web.json_response({"error": "no domain found"})

    async def address_to_available_ids(self, request):
        try:
            addr = request.rel_url.query["address"]
            ids = self.owners_db[addr]
            available = []
            for sid in ids:
                try:
                    self.tokenid_to_domain_db["id:" + str(sid)]
                    available.append(sid)
                except KeyError:
                    pass
            return web.json_response({"ids": available})
        except Exception:
            return web.json_response({"ids": []})

    async def uri(self, request):
        try:
            id = request.rel_url.query["id"]
            try:
                domain = self.tokenid_to_domain_db["id:" + str(id)]
                return web.json_response(
                    {
                        "name": domain,
                        "description": "This token represents an identity on StarkNet that can be linked to external services.",
                        "image": f"https://starknet.id/api/identicons/{id}",
                    }
                )
            except KeyError:
                return web.json_response(
                    {
                        "name": f"Starknet ID: {id}",
                        "description": "This token represents an identity on StarkNet that can be linked to external services.",
                        "image": f"https://starknet.id/api/identicons/{id}",
                    }
                )
        except Exception:
            return web.json_response({"error": "no id specified"})

    def build_app(self):
        app = web.Application()
        app.add_routes([web.get("/address_to_ids", self.address_to_ids)])
        app.add_routes(
            [web.get("/address_to_available_ids", self.address_to_available_ids)]
        )
        app.add_routes([web.get("/field_data_to_id", self.field_data_to_id)])
        app.add_routes([web.get("/uri", self.uri)])
        app.add_routes([web.get("/tokenid_to_domain", self.tokenid_to_domain)])
        app.add_routes([web.get("/domain_to_addr", self.domain_to_addr)])
        app.add_routes([web.get("/addr_to_domain", self.addr_to_domain)])

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
