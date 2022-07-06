import asyncio
from listener import Listener
from server.http import WebServer
from apibara import IndexerRunner
from apibara.model import EventFilter
from aiohttp import web
from config import TomlConfig
import shelve
import os


async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
    owners_db = shelve.open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "owners.shelf")
    )
    verified_db = shelve.open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "verified.shelf")
    )
    events_manager = Listener(owners_db, verified_db)
    asyncio.create_task(start_server(conf, owners_db, verified_db))
    runner = IndexerRunner(
        indexer_id=conf.indexer_id,
        new_events_handler=events_manager.handle_events,
    )
    runner.create_if_not_exists(
        filters=[
            EventFilter.from_event_name(name="Transfer", address=conf.contract_address),
            EventFilter.from_event_name(
                name="VerifiedData", address=conf.contract_address
            ),
        ],
        index_from_block=260_000,
    )

    await runner.run()


async def start_server(conf, owners_db, verified_db):
    app = WebServer(owners_db, verified_db).build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, port=conf.server_port).start()


if __name__ == "__main__":
    asyncio.run(main())
