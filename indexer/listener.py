from apibara import NewEvents, Info
from decoder import decode_transfer_event


class Listener:
    def __init__(self, db):
        self.db = db

    async def handle_events(self, _info: Info, block_events: NewEvents):
        print("[block] -", block_events.block_number)
        for event in block_events.events:
            decoded = decode_transfer_event(event.data)
            source = "" + str(decoded.from_address)
            target = "" + str(decoded.to_address)
            token_id = decoded.token_id.id
            if source != "0x0":
                source_ids = self.db.get(source, [])
                if source_ids:
                    source_ids.remove(token_id)
                self.db[source] = source_ids

            target_ids = self.db.get(target, [])
            target_ids.append(token_id)
            self.db[target] = target_ids
            print("-", token_id, source, "->", target)
