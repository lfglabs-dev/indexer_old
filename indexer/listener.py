from apibara import NewEvents, Info
from decoder import (
    decode_transfer_event,
    decode_verifier_data,
    decode_domain_to_addr_data,
    decode_addr_to_domain_data,
    decode_starknet_id_update,
)


class Listener:
    def __init__(
        self,
        owners_db,
        verified_db,
        domain_to_addr_db,
        addr_to_domain_db,
        tokenid_to_domain_db,
    ):
        self.owners_db = owners_db
        self.verified_db = verified_db
        self.domain_to_addr_db = domain_to_addr_db
        self.addr_to_domain_db = addr_to_domain_db
        self.tokenid_to_domain_db = tokenid_to_domain_db

    async def handle_events(self, _info: Info, block_events: NewEvents):
        print("[block] -", block_events.block.number)
        for event in block_events.events:
            if event.name == "Transfer":
                decoded = decode_transfer_event(event.data)
                source = "" + str(decoded.from_address)
                target = "" + str(decoded.to_address)
                token_id = decoded.token_id.id
                if source != "0x0":
                    source_ids = self.owners_db.get(source, [])
                    if source_ids and token_id in source_ids:
                        source_ids.remove(token_id)
                    self.owners_db[source] = source_ids

                target_ids = self.owners_db.get(target, [])
                target_ids.append(token_id)
                self.owners_db[target] = target_ids
                print("- [transfer]", token_id, source, "->", target)

            elif event.name == "VerifierDataUpdate":
                decoded = decode_verifier_data(event.data)
                key = (
                    str(decoded.field)
                    + ":"
                    + str(decoded.data)
                    + ":"
                    + str(decoded.verifier)
                )
                self.verified_db[key] = str(decoded.token_id)
                print("- [data_update]", key, "->", decoded.token_id)

            elif event.name == "domain_to_addr_update":
                decoded = decode_domain_to_addr_data(event.data)
                self.domain_to_addr_db[decoded.domain] = decoded.address
                print("- [domain2addr]", decoded.domain, "->", decoded.address)

            elif event.name == "addr_to_domain_update":
                decoded = decode_addr_to_domain_data(event.data)
                self.addr_to_domain_db[str(decoded.address)] = decoded.domain
                print("- [addr2domain]", decoded.address, "->", decoded.domain)

            elif event.name == "starknet_id_update":
                decoded = decode_starknet_id_update(event.data)
                self.tokenid_to_domain_db["id:" + str(decoded.owner)] = decoded.domain
                print("- [starknet_id2domain]", decoded.owner, "->", decoded.domain)

            elif event.name == "reset_subdomains_update":
                return

            else:
                print("error: event", event.name, "not supported")
