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
    database = shelve.open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "storage.shelf")
    )
    events_manager = Listener(database)
    asyncio.create_task(start_server(conf, database))
    runner = IndexerRunner(
        indexer_id=conf.indexer_id,
        new_events_handler=events_manager.handle_events,
    )
    runner.create_if_not_exists(
        filters=[
            EventFilter.from_event_name(name="Transfer", address=conf.contract_address)
        ],
        index_from_block=258_251,
    )

    await runner.run()


async def start_server(conf, database):
    app = WebServer(database).build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, port=conf.server_port).start()


if __name__ == "__main__":
    asyncio.run(main())
