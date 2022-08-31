import asyncio
from listener import Listener
from server.http import WebServer
from apibara import IndexerRunner
from apibara.indexer.runner import IndexerRunnerConfiguration
from apibara.model import EventFilter
from aiohttp import web
from config import TomlConfig
import shelve
import os


async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
    if conf.docker:
        owners_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "../data/owners.shelf"
            )
        )
        verified_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "../data/verified.shelf"
            )
        )
        domain_to_addr_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../data/domain_to_addr_db.shelf",
            )
        )
        addr_to_domain_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../data/addr_to_domain_db.shelf",
            )
        )
        tokenid_to_domain_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../data/tokenid_to_domain.shelf",
            )
        )
    else:
        owners_db = shelve.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "owners.shelf")
        )
        verified_db = shelve.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "verified.shelf")
        )
        domain_to_addr_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "domain_to_addr_db.shelf"
            )
        )
        addr_to_domain_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "addr_to_domain_db.shelf"
            )
        )
        tokenid_to_domain_db = shelve.open(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "tokenid_to_domain.shelf"
            )
        )
    events_manager = Listener(
        owners_db,
        verified_db,
        domain_to_addr_db,
        addr_to_domain_db,
        tokenid_to_domain_db,
    )
    asyncio.create_task(
        start_server(
            conf,
            owners_db,
            verified_db,
            domain_to_addr_db,
            addr_to_domain_db,
            tokenid_to_domain_db,
        )
    )
    if conf.docker:
        runner = IndexerRunner(
            config=IndexerRunnerConfiguration(
                apibara_url="apibara:7171",
                storage_url="mongodb://apibara:apibara@mongo:27017",
            ),
            network_name="starknet-goerli",
            indexer_id=conf.indexer_id,
            new_events_handler=events_manager.handle_events,
        )
    else:
        runner = IndexerRunner(
            config=IndexerRunnerConfiguration(
                storage_url="mongodb://apibara:apibara@localhost:27017"
            ),
            network_name="starknet-goerli",
            indexer_id=conf.indexer_id,
            new_events_handler=events_manager.handle_events,
        )
    runner.create_if_not_exists(
        filters=[
            EventFilter.from_event_name(
                name="Transfer", address=conf.starknetid_contract
            ),
            EventFilter.from_event_name(
                name="VerifiedData", address=conf.starknetid_contract
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
        index_from_block=260_000,  # 260_000 311_074
    )
    print("started")
    await runner.run()


async def start_server(
    conf,
    owners_db,
    verified_db,
    domain_to_addr_db,
    addr_to_domain_db,
    tokenid_to_domain_db,
):
    app = WebServer(
        owners_db,
        verified_db,
        domain_to_addr_db,
        addr_to_domain_db,
        tokenid_to_domain_db,
    ).build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, port=conf.server_port).start()


if __name__ == "__main__":
    asyncio.run(main())
