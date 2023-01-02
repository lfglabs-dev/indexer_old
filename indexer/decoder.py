from dataclasses import dataclass
import string
from typing import Iterator, List, Tuple


@dataclass
class TokenId:
    id: int

    def to_bytes(self) -> bytes:
        return int_to_bytes(self.id)


class Uint256TokenId(TokenId):
    pass


class FeltTokenId(TokenId):
    pass


@dataclass
class TransferEvent:
    from_address: int
    to_address: int
    token_id: TokenId


@dataclass
class SbtTransferEvent:
    sbt: int
    source: int
    target: int


@dataclass
class VerifierDataUpdate:
    token_id: int
    field: int
    data: int
    verifier: int


@dataclass
class UserDataUpdate:
    token_id: int
    field: int
    data: int


@dataclass
class DomainToAddrUpdate:
    domain: string
    address: int


@dataclass
class AddrToDomainUpdate:
    address: int
    domain: string


@dataclass
class StarknetIdUpdate:
    domain: string
    owner: int
    expiry: int


@dataclass
class DomainTransfer:
    domain: string
    prev_owner: int
    new_owner: int


@dataclass
class ResetSubdomainsUpdate:
    domain: string


class ERC721Contract:
    def __init__(self, rpc, address) -> None:
        self._rpc = rpc
        self._address = address

    async def is_erc721(self, token_id):
        # Check 1. Supports interface?
        try:
            response = await self._rpc.call(
                self._address, "supportsInterface", ["0x80ac58cd"]
            )
            return response == ["0x1"]
        except:
            pass

        # Check 2. Does tokenURI return anything?
        try:
            if isinstance(token_id, FeltTokenId):
                args = [hex(token_id.id)]
            elif isinstance(token_id, Uint256TokenId):
                low, high = _int_to_uint256(token_id.id)
                args = [hex(low), hex(high)]
            else:
                return False

            _ = await self._rpc.call(self._address, "tokenURI", args)
            return True
        except:
            pass
        return False

    async def name(self):
        try:
            name_response = await self._rpc.call(self._address, "name", [])
            return _decode_string_from_response(name_response)
        except:
            return None


def decode_transfer_event(data: List[bytes]) -> TransferEvent:
    if len(data) == 3:
        data_iter = iter(data)
        from_ = _felt_from_iter(data_iter)
        to = _felt_from_iter(data_iter)
        token_id = _felt_from_iter(data_iter)
        token_id = FeltTokenId(token_id)
        return TransferEvent(from_, to, token_id)
    elif len(data) == 4:
        data_iter = iter(data)
        from_ = _felt_from_iter(data_iter)
        to = _felt_from_iter(data_iter)
        token_id = _uint256_from_iter(data_iter)
        token_id = Uint256TokenId(token_id)
        return TransferEvent(from_, to, token_id)
    else:
        return None


def decode_verifier_data(data_input: List[bytes]) -> VerifierDataUpdate:
    data_iter = iter(data_input)
    token_id = _felt_from_iter(data_iter)
    field = _felt_from_iter(data_iter)
    data = _felt_from_iter(data_iter)
    verifier = _felt_from_iter(data_iter)

    return VerifierDataUpdate(token_id, field, data, verifier)


def decode_sbt_transfer(data_input: List[bytes]) -> SbtTransferEvent:
    data_iter = iter(data_input)
    sbt = _felt_from_iter(data_iter)
    source = _felt_from_iter(data_iter)
    target = _felt_from_iter(data_iter)

    return SbtTransferEvent(sbt, source, target)


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


# func domain_to_addr_update(domain_len : felt, domain : felt*, address : felt):
def decode_domain_to_addr_data(data_input: List[bytes]) -> DomainToAddrUpdate:
    data_iter = iter(data_input)

    arr_len = _felt_from_iter(data_iter)
    domain = ""
    for _ in range(arr_len):
        value = _felt_from_iter(data_iter)
        domain += decode_felt_to_domain_string(value) + "."
    if domain:
        domain += "stark"
    address = _felt_from_iter(data_iter)

    return DomainToAddrUpdate(domain, address)


def decode_addr_to_domain_data(data_input: List[bytes]) -> AddrToDomainUpdate:
    data_iter = iter(data_input)

    address = _felt_from_iter(data_iter)

    arr_len = _felt_from_iter(data_iter)
    domain = ""
    for _ in range(arr_len):
        value = _felt_from_iter(data_iter)
        domain += decode_felt_to_domain_string(value) + "."
    if domain:
        domain += "stark"

    return AddrToDomainUpdate(address, domain)


def decode_starknet_id_update(data_input: List[bytes]) -> StarknetIdUpdate:
    data_iter = iter(data_input)

    arr_len = _felt_from_iter(data_iter)
    domain = ""
    for _ in range(arr_len):
        value = _felt_from_iter(data_iter)
        domain += decode_felt_to_domain_string(value) + "."
    if domain:
        domain += "stark"
    owner = _felt_from_iter(data_iter)
    expiry = _felt_from_iter(data_iter)

    return StarknetIdUpdate(domain, owner, expiry)


def decode_domain_transfer(data_input: List[bytes]) -> DomainTransfer:
    data_iter = iter(data_input)

    arr_len = _felt_from_iter(data_iter)
    domain = ""
    for _ in range(arr_len):
        value = _felt_from_iter(data_iter)
        domain += decode_felt_to_domain_string(value) + "."
    if domain:
        domain += "stark"
    prev_owner = _felt_from_iter(data_iter)
    new_owner = _felt_from_iter(data_iter)

    return DomainTransfer(domain, prev_owner, new_owner)


def decode_reset_subdomains_update(data_input: List[bytes]) -> ResetSubdomainsUpdate:
    data_iter = iter(data_input)

    arr_len = _felt_from_iter(data_iter)
    domain = ""
    for _ in range(arr_len):
        value = _felt_from_iter(data_iter)
        domain += decode_felt_to_domain_string(value) + "."
    if domain:
        domain += "stark"

    return ResetSubdomainsUpdate(domain)


def hex_to_bytes(s: str) -> bytes:
    s = s.replace("0x", "")
    # Python doesn't like odd-numbered hex strings
    if len(s) % 2 == 1:
        s = "0" + s
    return bytes.fromhex(s)


def int_to_bytes(n: int) -> bytes:
    return n.to_bytes(32, "big")


def bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, "big")


def _uint256_from_iter(it: Iterator[bytes]):
    low = _felt_from_iter(it)
    high = _felt_from_iter(it)
    return (high << 128) + low


def _int_to_uint256(n: int) -> Tuple[int, int]:
    high = n >> 128
    low = n - (high << 128)
    return low, high


def _felt_from_iter(it: Iterator[bytes]):
    return bytes_to_int(next(it))


def _decode_string_from_response(data: List[str]):
    if len(data) == 1:
        return _decode_short_string(iter(data))
    return _decode_long_string(iter(data))


def _decode_short_string(it: Iterator[str]):
    return hex_to_bytes(next(it)).decode("ascii")


def _decode_long_string(it: Iterator[str]):
    string_len = bytes_to_int(hex_to_bytes(next(it)))
    acc = ""
    for _ in range(string_len):
        acc += _decode_short_string(it)
    return acc
