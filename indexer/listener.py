from apibara import NewEvents, Info
from decoder import (
    decode_transfer_event,
    decode_verifier_data,
    decode_domain_to_addr_data,
    decode_addr_to_domain_data,
    decode_starknet_id_update,
    decode_domain_transfer,
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

                # update existing owner
                existing = False
                if source != "0":
                    existing = await _info.storage.find_one_and_update(
                        "starknet_ids",
                        {"token_id": str(token_id), "_chain.valid_to": None},
                        {"$set": {"owner": str(source)}},
                    )
                if not existing:
                    await _info.storage.insert_one(
                        "starknet_ids",
                        {
                            "owner": str(target),
                            "token_id": str(token_id),
                            "creation_date": block_events.block.timestamp,
                        },
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
                    + hex(decoded.verifier)
                )
                print("- [data_update]", decoded.token_id, "->", key)

            elif event.name == "domain_to_addr_update":
                decoded = decode_domain_to_addr_data(event.data)
                if decoded.domain:
                    await _info.storage.find_one_and_update(
                        "domains",
                        {"domain": decoded.domain, "_chain.valid_to": None},
                        {"$set": {"addr": str(decoded.address)}},
                    )
                else:
                    await _info.storage.find_one_and_update(
                        "domains",
                        {"domain": decoded.domain, "_chain.valid_to": None},
                        {"$unset": {"addr": None}},
                    )
                print("- [domain2addr]", decoded.domain, "->", hex(decoded.address))

            elif event.name == "addr_to_domain_update":
                decoded = decode_addr_to_domain_data(event.data)
                await _info.storage.find_one_and_update(
                    "domains",
                    {"rev_addr": str(decoded.address), "_chain.valid_to": None},
                    {"$unset": {"rev_addr": None}},
                )
                if decoded.domain:
                    await _info.storage.find_one_and_update(
                        "domains",
                        {"domain": decoded.domain, "_chain.valid_to": None},
                        {"$set": {"rev_addr": str(decoded.address)}},
                    )
                print("- [addr2domain]", hex(decoded.address), "->", decoded.domain)

            elif event.name == "starknet_id_update":
                decoded = decode_starknet_id_update(event.data)
                # we want to upsert
                existing = await _info.storage.find_one_and_update(
                    "domains",
                    {"domain": decoded.domain, "_chain.valid_to": None},
                    {
                        "$set": {
                            "domain": decoded.domain,
                            "expiry": decoded.expiry,
                            "token_id": str(decoded.owner),
                        }
                    },
                )
                if existing is None:
                    await _info.storage.insert_one(
                        "domains",
                        {
                            "domain": decoded.domain,
                            "expiry": decoded.expiry,
                            "token_id": str(decoded.owner),
                            "creation_date": block_events.block.timestamp,
                        },
                    )
                    print(
                        "- [purchased]",
                        "domain:",
                        decoded.domain,
                        "id:",
                        decoded.owner,
                    )
                else:
                    await _info.storage.insert_one(
                        "domains_renewals",
                        {
                            "domain": decoded.domain,
                            "prev_expiry": existing["expiry"],
                            "new_expiry": decoded.expiry,
                            "renewal_date": block_events.block.timestamp,
                        },
                    )
                    print(
                        "- [renewed]",
                        "domain:",
                        decoded.domain,
                        "id:",
                        decoded.owner,
                    )

            elif event.name == "domain_transfer":
                decoded = decode_domain_transfer(event.data)
                if decoded.prev_owner:
                    await _info.storage.find_one_and_update(
                        "domains",
                        {
                            "domain": decoded.domain,
                            "token_id": str(decoded.prev_owner),
                            "_chain.valid_to": None,
                        },
                        {"$set": {"token_id": str(decoded.new_owner)}},
                    )
                else:
                    await _info.storage.insert_one(
                        "domains",
                        {
                            "domain": decoded.domain,
                            "addr": "0",
                            "expiry": None,
                            "token_id": str(decoded.new_owner),
                        },
                    )

                print(
                    "- [domain_transfer]",
                    decoded.domain,
                    decoded.prev_owner,
                    "->",
                    decoded.new_owner,
                )

            elif event.name == "reset_subdomains_update":
                return

            else:
                print("error: event", event.name, "not supported")
