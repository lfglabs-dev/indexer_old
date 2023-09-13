from apibara.starknet import EventFilter, Filter, StarkNetIndexer, felt
from starknet_py.contract import ContractFunction
from apibara.indexer import Info
from apibara.starknet.cursor import starknet_cursor
from apibara.protocol.proto.stream_pb2 import Cursor, DataFinality
from apibara.indexer.indexer import IndexerConfiguration
from apibara.starknet.proto.starknet_pb2 import Block
from apibara.starknet.proto.types_pb2 import FieldElement
from typing import List


def decode_felt_to_domain_string(felt):
    def extract_stars(str):
        k = 0
        while str.endswith(bigAlphabet[-1]):
            str = str[:-1]
            k += 1
        return (str, k)

    basicAlphabet = "abcdefghijklmnopqrstuvwxyz0123456789-"
    bigAlphabet = "这来"

    decoded = ""
    while felt != 0:
        code = felt % (len(basicAlphabet) + 1)
        felt = felt // (len(basicAlphabet) + 1)
        if code == len(basicAlphabet):
            next_felt = felt // (len(bigAlphabet) + 1)
            if next_felt == 0:
                code2 = felt % (len(bigAlphabet) + 1)
                felt = next_felt
                decoded += basicAlphabet[0] if code2 == 0 else bigAlphabet[code2 - 1]
            else:
                decoded += bigAlphabet[felt % len(bigAlphabet)]
                felt = felt // len(bigAlphabet)
        else:
            decoded += basicAlphabet[code]

    decoded, k = extract_stars(decoded)
    if k:
        decoded += (
            ((bigAlphabet[-1] * (k // 2 - 1)) + bigAlphabet[0] + basicAlphabet[1])
            if k % 2 == 0
            else bigAlphabet[-1] * (k // 2 + 1)
        )

    return decoded


class Listener(StarkNetIndexer):
    def __init__(self, conf, logger) -> None:
        super().__init__()
        self.conf = conf
        self.logger = logger
        self.handle_pending_data = self.handle_data

    def check_is_subdomain(self, contract: FieldElement):
        if felt.to_int(contract) == int(self.conf.braavos_contract, 16):
            return (True, "braavos")
        elif felt.to_int(contract) == int(self.conf.xplorer_contract, 16):
            return (True, "xplorer")
        else:
            return (False, "")

    def indexer_id(self) -> str:
        return self.conf.indexer_id

    def initial_configuration(self) -> Filter:
        filter = Filter().with_header(weak=True)
        self.event_map = dict()

        def add_filter(contract, event):
            selector = ContractFunction.get_selector(event)
            self.event_map[selector] = event
            filter.add_event(
                EventFilter()
                .with_from_address(felt.from_hex(contract))
                .with_keys([felt.from_int(selector)])
            )

        # # starknet_id contract
        # for starknet_id_event in [
        #     "Transfer",
        #     "VerifierDataUpdate",
        #     "on_inft_equipped",
        # ]:
        #     add_filter(self.conf.starknetid_contract, starknet_id_event)

        # naming contract
        for starknet_id_event in [
            # "domain_to_addr_update",
            # "addr_to_domain_update",
            # "starknet_id_update",
            # "domain_transfer",
            # "reset_subdomains_update",
            "domain_to_resolver_update",
        ]:
            add_filter(self.conf.naming_contract, starknet_id_event)

        # # braavos subdomain contract
        # for starknet_id_event in [
        #     "domain_to_addr_update",
        # ]:
        #     add_filter(self.conf.braavos_contract, starknet_id_event)

        # # xplorer subdomain contract
        # for starknet_id_event in [
        #     "domain_to_addr_update",
        # ]:
        #     add_filter(self.conf.xplorer_contract, starknet_id_event)

        # # referral contract
        # for starknet_id_event in [
        #     "on_claim",
        #     "on_commission",
        # ]:
        #     add_filter(self.conf.referral_contract, starknet_id_event)

        return IndexerConfiguration(
            filter=filter,
            starting_cursor=starknet_cursor(self.conf.starting_block),
            finality=DataFinality.DATA_STATUS_ACCEPTED
            if self.conf.is_devnet is True
            else DataFinality.DATA_STATUS_PENDING,
        )

    async def handle_data(self, info: Info, block: Block):
        # Handle one block of data
        for event_with_tx in block.events:
            tx_hash = felt.to_hex(event_with_tx.transaction.meta.hash)
            event = event_with_tx.event
            event_name = self.event_map[felt.to_int(event.keys[0])]

            await {
                # "Transfer": self.on_starknet_id_transfer,
                # "VerifierDataUpdate": self.on_verifier_data_update,
                # "on_inft_equipped": self.on_inft_equipped,
                # "domain_to_addr_update": self.domain_to_addr_update,
                # "addr_to_domain_update": self.addr_to_domain_update,
                "domain_to_resolver_update": self.domain_to_resolver_update,
                # "starknet_id_update": self.starknet_id_update,
                # "domain_transfer": self.domain_transfer,
                # "reset_subdomains_update": self.reset_subdomains_update,
                # "on_claim": self.referral_on_claim,
                # "on_commission": self.referral_on_commission,
            }[event_name](info, block, event.from_address, event.data)

    async def on_starknet_id_transfer(
        self, info: Info, block: Block, _: FieldElement, data: List[FieldElement]
    ):
        source = str(felt.to_int(data[0]))
        target = str(felt.to_int(data[1]))
        token_id = str(felt.to_int(data[2]) + (felt.to_int(data[3]) << 128))
        # update existing owner
        existing = False
        if source != "0":
            existing = await info.storage.find_one_and_update(
                "starknet_ids",
                {"token_id": token_id, "_chain.valid_to": None},
                {"$set": {"owner": target}},
            )
        if not existing:
            await info.storage.insert_one(
                "starknet_ids",
                {
                    "owner": target,
                    "token_id": token_id,
                    "creation_date": block.header.timestamp.ToDatetime(),
                },
            )

        self.logger.local("- [transfer] %s %s -> %s" % (token_id, source, target))

    async def on_verifier_data_update(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        token_id = str(felt.to_int(data[0]))
        field = str(felt.to_int(data[1]))
        verifier_data = str(felt.to_int(data[2]))
        verifier_felt = data[3]
        verifier = str(felt.to_int(verifier_felt))

        await info.storage.find_one_and_replace(
            "starknet_ids_data",
            {
                "token_id": token_id,
                "verifier": verifier,
                "field": field,
                "_chain.valid_to": None,
            },
            {
                "token_id": token_id,
                "verifier": verifier,
                "field": field,
                "data": verifier_data,
                "_chain.valid_to": None,
            },
            upsert=True,
        )
        key = field + ":" + verifier_data + ":" + felt.to_hex(verifier_felt)
        self.logger.local("- [data_update] %s -> %s" % (token_id, key))

    async def on_inft_equipped(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        contract = felt.to_hex(data[0])
        inft_id = str(felt.to_int(data[1]))
        starknet_id = str(felt.to_int(data[2]))

        if starknet_id:
            await info.storage.find_one_and_replace(
                "equipped_infts",
                {
                    "contract": contract,
                    "inft_id": inft_id,
                    "_chain.valid_to": None,
                },
                {
                    "contract": contract,
                    "inft_id": inft_id,
                    "starknet_id": starknet_id,
                    "_chain.valid_to": None,
                },
                upsert=True,
            )
            self.logger.local(
                "- [inft equipped] %s inft: %s starknet_id: %s"
                % (contract, inft_id, starknet_id)
            )

        else:
            await info.storage.delete_one(
                "equipped_infts",
                {
                    "contract": contract,
                    "inft_id": inft_id,
                    "_chain.valid_to": None,
                },
            )
            self.logger.local("- [inft unequipped] %s inft: %s" % (contract, inft_id))

    async def domain_to_addr_update(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        (is_subdomain, project) = self.check_is_subdomain(contract)
        arr_len = felt.to_int(data[0])
        domain = ""
        for i in range(arr_len):
            domain += decode_felt_to_domain_string(felt.to_int(data[1 + i])) + "."
        if domain:
            if is_subdomain:
                domain += project + "."
            domain += "stark"
        address = data[arr_len + 1]

        if domain:
            if is_subdomain:
                existing = await info.storage.find_one_and_update(
                    "subdomains",
                    {"domain": domain, "_chain.valid_to": None},
                    {
                        "$set": {
                            "project": project,
                            "addr": str(felt.to_int(address)),
                        }
                    },
                )
                if existing is None:
                    await info.storage.insert_one(
                        "subdomains",
                        {
                            "domain": domain,
                            "project": project,
                            "creation_date": block.header.timestamp.ToDatetime(),
                            "addr": str(felt.to_int(address)),
                        },
                    )
            else:
                await info.storage.find_one_and_update(
                    "domains",
                    {"domain": domain, "_chain.valid_to": None},
                    {"$set": {"addr": str(felt.to_int(address))}},
                )
        else:
            if is_subdomain:
                await info.storage.find_one_and_update(
                    "subdomains",
                    {"domain": domain, "project": project, "_chain.valid_to": None},
                    {"$unset": {"addr": None}},
                )
            else:
                await info.storage.find_one_and_update(
                    "domains",
                    {"domain": domain, "_chain.valid_to": None},
                    {"$unset": {"addr": None}},
                )
        self.logger.local("- [domain2addr] %s -> %s" % (domain, felt.to_hex(address)))

    async def domain_to_resolver_update(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        arr_len = felt.to_int(data[0])
        domain = ""
        for i in range(arr_len):
            domain += decode_felt_to_domain_string(felt.to_int(data[1 + i])) + "."
        if domain:
            domain += "stark"
        resolver = felt.to_int(data[arr_len + 1])
        if resolver == 0:
            await info.storage.delete_one(
                "custom_resolving",
                {"domain": domain, "_chain.valid_to": None},
            )
        else:
            existing = await info.storage.find_one_and_update(
                "custom_resolving",
                {"domain": domain, "_chain.valid_to": None},
                {
                    "$set": {
                        "domain": domain,
                        "resolver": str(resolver),
                    }
                },
            )
            if existing is None:
                await info.storage.insert_one(
                    "custom_resolving",
                    {
                        "domain": domain,
                        "resolver": str(resolver),
                    },
                )

        self.logger.local("- [domain2resolver] %s -> %s" % (domain, hex(resolver)))

    async def addr_to_domain_update(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        address = data[0]
        arr_len = felt.to_int(data[1])
        domain = ""
        for i in range(arr_len):
            domain += decode_felt_to_domain_string(felt.to_int(data[2 + i])) + "."
        if domain:
            domain += "stark"

        str_address = str(felt.to_int(address))

        await info.storage.find_one_and_update(
            "domains",
            {"rev_addr": str_address, "_chain.valid_to": None},
            {"$unset": {"rev_addr": None}},
        )
        if domain:
            if domain.endswith(".braavos.stark") or domain.endswith(".xplorer.stark"):
                await info.storage.find_one_and_update(
                    "subdomains",
                    {"domain": domain, "_chain.valid_to": None},
                    {"$set": {"rev_addr": str_address}},
                )
            else:
                await info.storage.find_one_and_update(
                    "domains",
                    {"domain": domain, "_chain.valid_to": None},
                    {"$set": {"rev_addr": str_address}},
                )
        self.logger.local("- [addr2domain] %s -> %s" % (felt.to_hex(address), domain))

    async def starknet_id_update(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        arr_len = felt.to_int(data[0])
        domain = ""
        for i in range(arr_len):
            domain += decode_felt_to_domain_string(felt.to_int(data[1 + i])) + "."
        if domain:
            domain += "stark"
        owner = str(felt.to_int(data[arr_len + 1]))
        expiry = felt.to_int(data[arr_len + 2])

        # we want to upsert
        existing = await info.storage.find_one_and_update(
            "domains",
            {"domain": domain, "_chain.valid_to": None},
            {
                "$set": {
                    "domain": domain,
                    "expiry": expiry,
                    "token_id": owner,
                }
            },
        )
        if existing is None:
            await info.storage.insert_one(
                "domains",
                {
                    "domain": domain,
                    "expiry": expiry,
                    "token_id": owner,
                    "creation_date": block.header.timestamp.ToDatetime(),
                },
            )
            self.logger.local("- [purchased] domain: %s id: %s" % (domain, owner))
        else:
            await info.storage.insert_one(
                "domains_renewals",
                {
                    "domain": domain,
                    "prev_expiry": existing["expiry"],
                    "new_expiry": expiry,
                    "renewal_date": block.header.timestamp.ToDatetime(),
                },
            )
            self.logger.local(
                "- [renewed] domain: %s id: %s time: %s days"
                % (domain, owner, (expiry - int(existing["expiry"])) / 86400)
            )

    async def domain_transfer(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        arr_len = felt.to_int(data[0])
        domain = ""
        for i in range(arr_len):
            domain += decode_felt_to_domain_string(felt.to_int(data[1 + i])) + "."
        if domain:
            domain += "stark"
        prev_owner = str(felt.to_int(data[arr_len + 1]))
        new_owner = str(felt.to_int(data[arr_len + 2]))

        if prev_owner != "0":
            await info.storage.find_one_and_update(
                "domains",
                {
                    "domain": domain,
                    "token_id": prev_owner,
                    "_chain.valid_to": None,
                },
                {"$set": {"token_id": new_owner}},
            )
        else:
            await info.storage.insert_one(
                "domains",
                {
                    "domain": domain,
                    "addr": "0",
                    "expiry": None,
                    "token_id": new_owner,
                    "creation_date": block.header.timestamp.ToDatetime(),
                },
            )

        self.logger.local(
            "- [domain_transfer] %s %s -> %s" % (domain, prev_owner, new_owner)
        )

    async def reset_subdomains_update(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        arr_len = felt.to_int(data[0])
        domain = ""
        for i in range(arr_len):
            domain += decode_felt_to_domain_string(felt.to_int(data[1 + i])) + "."
        if domain:
            domain += "stark"

        await info.storage.delete_many(
            "domains",
            {"domain": {"$regex": ".*\." + domain.replace(".", "\.")}},
        )
        self.logger.local("- [reset_subdomains] %s" % domain)

    async def referral_on_commission(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        amount = felt.to_int(data[1]) + (felt.to_int(data[2]) << 128)
        sponsor_addr = str(felt.to_int(data[3]))

        await info.storage.insert_one(
            "referral_revenues",
            {
                "timestamp": block.header.timestamp.ToDatetime(),
                "sponsor_addr": sponsor_addr,
                "amount": amount,
            },
        )
        self.logger.local(
            "- [add_commission] sponsor_addr: %s amount: %s timestamp: %s"
            % (sponsor_addr, amount, block.header.timestamp.ToDatetime())
        )

    async def referral_on_claim(
        self, info: Info, block: Block, contract: FieldElement, data: List[FieldElement]
    ):
        amount = felt.to_int(data[1]) + (felt.to_int(data[2]) << 128)
        sponsor_addr = str(felt.to_int(data[3]))

        await info.storage.insert_one(
            "referral_revenues",
            {
                "timestamp": block.header.timestamp.ToDatetime(),
                "sponsor_addr": sponsor_addr,
                "amount": -amount,
            },
        )
        self.logger.local(
            "- [on_claim] sponsor_addr: %s amount: %s timestamp: %s"
            % (sponsor_addr, -amount, block.header.timestamp.ToDatetime())
        )
