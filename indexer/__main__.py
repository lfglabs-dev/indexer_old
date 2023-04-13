import asyncio
import traceback
from listener import Listener
from apibara.indexer import IndexerRunner, IndexerRunnerConfiguration
from config import TomlConfig


async def main():
    conf = TomlConfig("config.toml", "config.template.toml")
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
