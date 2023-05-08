import asyncio
import traceback
from listener import Listener
from apibara.indexer import IndexerRunner, IndexerRunnerConfiguration
from pymongo import MongoClient
from config import TomlConfig

def create_indexes(conf):
    client = MongoClient(conf.connection_string)
    db = client[conf.indexer_id]

    with open("indexes.json", "r") as f:
        collections_and_indexes = json.load(f)

    for collection, indexes in collections_and_indexes.items():
        for index in indexes:
            db[collection].create_index(index['key'], name=index['name'])

    client.close()

async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
    create_indexes(conf)
    events_manager = Listener(conf)
    runner = IndexerRunner(
        config=IndexerRunnerConfiguration(
            stream_url=conf.apibara_stream,
            storage_url=conf.connection_string,
            token=conf.token
        ),
        reset_state=conf.reset_state,
    )

    await runner.run(events_manager, ctx={"network": "starknet-mainnet"})
    print("starknetid indexer started")


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception:
            print(traceback.format_exc())
            print("warning: exception detected, restarting")
