from apibara import NewEvents, Info
from decoder import (
    decode_transfer_event,
    decode_verifier_data,
    decode_domain_to_addr_data,
    decode_addr_to_domain_data,
    decode_starknet_id_update,
)


class Listener:
    async def handle_events(self, _info: Info, block_events: NewEvents):

        print("[block] -", block_events.block.number)
        for event in block_events.events:
            if event.name == "Transfer":
                decoded = decode_transfer_event(event.data)
                source = "" + str(decoded.from_address)
                target = "" + str(decoded.to_address)
                token_id = decoded.token_id.id

                # removing previous owner
                if source != "0x0":
                    await _info.storage.delete_one(
                        "starknet_ids",
                        {
                            "owner": str(source),
                            "token_id": str(token_id),
                            "_chain.valid_to": None,
                        },
                    )

                await _info.storage.insert_one(
                    "starknet_ids", {"owner": str(target), "token_id": str(token_id)}
                )
                print("- [transfer]", token_id, source, "->", target)

            elif event.name == "VerifierDataUpdate":
                decoded = decode_verifier_data(event.data)
                await _info.storage.find_one_and_replace(
                    "starknet_ids_data",
                    {
                        "token_id": str(decoded.token_id),
                        "verifier": str(decoded.verifier),
                        "field": str(decoded.field),
                    },
                    {
                        "token_id": str(decoded.token_id),
                        "verifier": str(decoded.verifier),
                        "field": str(decoded.field),
                        "data": str(decoded.data),
                        "_chain.valid_to": None,
                    },
                    upsert=True,
                )
                key = (
                    str(decoded.field)
                    + ":"
                    + str(decoded.data)
                    + ":"
                    + str(decoded.verifier)
                )
                print("- [data_update]", key, "->", decoded.token_id)

            elif event.name == "domain_to_addr_update":
                decoded = decode_domain_to_addr_data(event.data)
                await _info.storage.find_one_and_update(
                    "domains",
                    {"domain": decoded.domain, "_chain.valid_to": None},
                    {"$set": {"rev_addr": str(decoded.address)}},
                )
                print("- [domain2addr]", decoded.domain, "->", decoded.address)

            elif event.name == "addr_to_domain_update":
                decoded = decode_addr_to_domain_data(event.data)
                if decoded.domain:
                    await _info.storage.find_one_and_update(
                        "domains",
                        {"domain": decoded.domain, "_chain.valid_to": None},
                        {"$set": {"addr": str(decoded.address)}},
                    )
                else:
                    await _info.storage.delete_one(
                        "domains", {"domain": decoded.domain}
                    )
                print("- [addr2domain]", decoded.address, "->", decoded.domain)

            elif event.name == "starknet_id_update":
                decoded = decode_starknet_id_update(event.data)
                if decoded.domain:
                    await _info.storage.find_one_and_replace(
                        "domains",
                        {"domain": decoded.domain, "_chain.valid_to": None},
                        {
                            "domain": decoded.domain,
                            "expiry": decoded.expiry,
                            "token_id": str(decoded.owner),
                        },
                        upsert=True,
                    )
                else:
                    await _info.storage.delete_one(
                        "domains", {"token_id": str(decoded.owner)}
                    )
                print("- [starknet_id2domain]", decoded.owner, "->", decoded.domain)

            elif event.name == "reset_subdomains_update":
                return

            else:
                print("error: event", event.name, "not supported")
