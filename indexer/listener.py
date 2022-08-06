from apibara import NewEvents, Info
from decoder import decode_transfer_event, decode_verifier_data


class Listener:
    def __init__(self, owners_db, verified_db):
        self.owners_db = owners_db
        self.verified_db = verified_db

    async def handle_events(self, _info: Info, block_events: NewEvents):
        print("[block] -", block_events.block_number)
        for event in block_events.events:
            if event.name == "Transfer":
                decoded = decode_transfer_event(event.data)
                source = "" + str(decoded.from_address)
                target = "" + str(decoded.to_address)
                token_id = decoded.token_id.id
                if source != "0x0":
                    source_ids = self.owners_db.get(source, [])
                    if source_ids:
                        source_ids.remove(token_id)
                    self.owners_db[source] = source_ids

                target_ids = self.owners_db.get(target, [])
                target_ids.append(token_id)
                self.owners_db[target] = target_ids
                print("- [transfer]", token_id, source, "->", target)
            elif event.name == "VerifiedData":
                decoded = decode_verifier_data(event.data)
                key = (
                    str(decoded.type)
                    + ":"
                    + str(decoded.data)
                    + ":"
                    + str(decoded.verifier)
                )
                self.verified_db[key] = str(decoded.token_id.id)
                print("- [data_update]", key, "->", decoded.token_id.id)
            else:
                print("error: event", event.name, "not supported")
