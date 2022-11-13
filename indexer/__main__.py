import asyncio
from listener import Listener
from server.http import WebServer
from apibara import EventFilter, IndexerRunner
from apibara.indexer import IndexerRunnerConfiguration
from aiohttp import web
from config import TomlConfig
from pymongo import MongoClient
import shelve
import os


async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
    events_manager = Listener()
    runner = IndexerRunner(
        config=IndexerRunnerConfiguration(
            apibara_url="goerli.starknet.stream.apibara.com:443",
            storage_url=conf.connection_string,
        ),
        reset_state=conf.reset_state,
        indexer_id=conf.indexer_id,
        new_events_handler=events_manager.handle_events,
    )
    _mongo = MongoClient(conf.connection_string)
    db_name = conf.indexer_id.replace("-", "_")
    asyncio.create_task(start_server(conf, _mongo[db_name]))

    runner.create_if_not_exists(
        filters=[
            EventFilter.from_event_name(
                name="Transfer", address=conf.starknetid_contract
            ),
            EventFilter.from_event_name(
                name="VerifierDataUpdate", address=conf.starknetid_contract
            ),
            EventFilter.from_event_name(
                name="domain_to_addr_update", address=conf.naming_contract
            ),
            EventFilter.from_event_name(
                name="addr_to_domain_update", address=conf.naming_contract
            ),
            EventFilter.from_event_name(
                name="starknet_id_update", address=conf.naming_contract
            ),
            EventFilter.from_event_name(
                name="reset_subdomains_update", address=conf.naming_contract
            ),
        ],
        index_from_block=conf.starting_block,
    )
    print("started")
    await runner.run()


async def start_server(conf, database):
    app = WebServer(database).build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, port=conf.server_port).start()


if __name__ == "__main__":
    asyncio.run(main())
