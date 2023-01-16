import asyncio
from listener import Listener
from apibara import EventFilter, IndexerRunner
from apibara.indexer import IndexerRunnerConfiguration
from config import TomlConfig
from pymongo import MongoClient


async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
    events_manager = Listener()
    runner = IndexerRunner(
        config=IndexerRunnerConfiguration(
            apibara_url=conf.apibara_stream,
            storage_url=conf.connection_string,
        ),
        reset_state=conf.reset_state,
        indexer_id=conf.indexer_id,
        new_events_handler=events_manager.handle_events,
    )
    runner.add_pending_events_handler(events_manager.handle_events, interval_seconds=5)
    runner.create_if_not_exists(
        filters=[
            EventFilter.from_event_name(
                name="Transfer", address=conf.starknetid_contract
            ),
            EventFilter.from_event_name(
                name="VerifierDataUpdate", address=conf.starknetid_contract
            ),
            EventFilter.from_event_name(
                name="on_inft_equipped", address=conf.starknetid_contract
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
                name="domain_transfer", address=conf.naming_contract
            ),
            EventFilter.from_event_name(
                name="reset_subdomains_update", address=conf.naming_contract
            ),
            EventFilter.from_event_name(name="sbt_transfer"),
        ],
        index_from_block=conf.starting_block,
    )
    print("starknetid indexer started")
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
