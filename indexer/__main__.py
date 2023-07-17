import asyncio
import traceback
from listener import Listener
from apibara.indexer import IndexerRunner, IndexerRunnerConfiguration
from pymongo import MongoClient
from config import TomlConfig
import json
from logger import Logger


def create_indexes(conf):
    client = MongoClient(conf.connection_string)
    db = client[conf.indexer_id]

    with open("indexes.json", "r") as f:
        collections_and_indexes = json.load(f)

    for collection, indexes in collections_and_indexes.items():
        for index in indexes:
            index_keys = [(k, v) for k, v in index["key"].items()]
            db[collection].create_index(index_keys, name=index["name"])

    client.close()


async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
    logger = Logger(conf)
    create_indexes(conf)
    events_manager = Listener(conf, logger)
    enable_ssl = not conf.is_devnet
    runner = IndexerRunner(
        config=IndexerRunnerConfiguration(
            stream_url=conf.apibara_stream,
            storage_url=conf.connection_string,
            token=conf.token,
            stream_ssl=enable_ssl,
        ),
        reset_state=conf.reset_state,
    )
    logger.info("starting starknetid indexer")
    await runner.run(events_manager, ctx={"network": "starknet-mainnet"})


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            conf = TomlConfig(
                "config.toml", "config.template.toml"
            )  # create a new config object
            logger = Logger(conf)  # create an instance of Logger
            exception_traceback = traceback.format_exc()  # get the traceback
            print(exception_traceback)  # print it locally
            logger.warning(
                f"warning: {type(e).__name__} detected, restarting"
            )  # only send the exception type to the server
