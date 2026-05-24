import hashlib
import hmac
import struct

from ecdsa import SECP256k1
from ecdsa.ellipticcurve import PointJacobi

from src.mnemonic import mnemonic_to_seed

_CURVE = SECP256k1.curve
_G = SECP256k1.generator
_ORDER = SECP256k1.order


def _int_from(b):
    return int.from_bytes(b, "big")


def _int_to(i, n=32):
    return i.to_bytes(n, "big")


def _hmac512(k, d):
    return hmac.new(k, d, hashlib.sha512).digest()


def _point_ser(p, comp=True):
    x = _int_to(p.x(), 32)
    if comp:
        prefix = b"\x02" if p.y() % 2 == 0 else b"\x03"
        return prefix + x
    y = _int_to(p.y(), 32)
    return b"\x04" + x + y


def _point_add(p1, p2):
    return p1 + p2


def _point_mul(p, k):
    return p * k


def _sha256(d):
    return hashlib.sha256(d).digest()


def _ripemd160(d):
    h = hashlib.new("ripemd160")
    h.update(d)
    return h.digest()


def _hash160(d):
    return _ripemd160(_sha256(d))


def _double_sha(d):
    return _sha256(_sha256(d))


def _bip32_ckd(k_par, c_par, index):
    hardened = index >= 0x80000000
    if hardened:
        data = b"\x00" + _int_to(k_par) + struct.pack(">I", index)
    else:
        data = _point_ser(_point_mul(_G, k_par), True) + struct.pack(">I", index)
    I = _hmac512(c_par, data)
    k = (_int_from(I[:32]) + k_par) % _ORDER
    c = I[32:]
    return k, c, _point_mul(_G, k)


def _seed_to_master(seed):
    I = _hmac512(b"Bitcoin seed", seed)
    k = _int_from(I[:32])
    c = I[32:]
    return k, c, _point_mul(_G, k)


def _derive_path(seed, path_str):
    if isinstance(seed, str):
        seed = seed.encode()
    k, c, _ = _seed_to_master(seed)
    for seg in path_str.strip("m/").split("/"):
        idx = int(seg.replace("'", ""))
        if "'" in seg:
            idx += 0x80000000
        k, c, _ = _bip32_ckd(k, c, idx)
    return k, c, _point_mul(_G, k)


def _pub_to_p2pkh(pub, version=b"\x00"):
    net = version + _hash160(pub)
    return _base58(net + _double_sha(net)[:4])


def _pub_to_p2sh_p2wpkh(pub, version=b"\x05"):
    wit = _hash160(pub)
    script = b"\x00\x14" + wit
    net = version + _hash160(script)
    return _base58(net + _double_sha(net)[:4])


def _pub_to_p2wpkh(pub, hrp="bc"):
    wit = _hash160(pub)
    return _segwit_addr(hrp, 0, wit)


def _segwit_addr(hrp, witver, witprog):
    data = [witver] + _convertbits(list(witprog), 8, 5)
    return _bech32(hrp, data)


def _bech32_polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1:
                chk ^= gen[i]
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _bech32_checksum(hrp, data):
    vals = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(vals + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


_B32CH = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32(hrp, data):
    return hrp + "1" + "".join(_B32CH[d] for d in data + _bech32_checksum(hrp, data))


def _convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for v in data:
        acc = (acc << frombits) | v
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret


_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58(data):
    n = _int_from(data)
    res = []
    while n > 0:
        n, r = divmod(n, 58)
        res.append(_B58[r])
    for b in data:
        if b == 0:
            res.append("1")
        else:
            break
    return "".join(reversed(res))


def derive_btc_like(seed, coin_type, account=0, address_index=0):
    pub44 = _point_ser(_derive_path(seed, f"m/44'/{coin_type}'/{account}'/0/{address_index}")[2], True)
    pub49 = _point_ser(_derive_path(seed, f"m/49'/{coin_type}'/{account}'/0/{address_index}")[2], True)
    pub84 = _point_ser(_derive_path(seed, f"m/84'/{coin_type}'/{account}'/0/{address_index}")[2], True)

    if coin_type == 0:  # Bitcoin
        return {
            "p2pkh": _pub_to_p2pkh(pub44, b"\x00"),
            "p2sh": _pub_to_p2sh_p2wpkh(pub49, b"\x05"),
            "p2wkh": _pub_to_p2wpkh(pub84, "bc"),
        }
    elif coin_type == 2:  # Litecoin
        return {
            "p2pkh": _pub_to_p2pkh(pub44, b"\x30"),
            "p2sh": _pub_to_p2sh_p2wpkh(pub49, b"\x32"),
            "p2wkh": _pub_to_p2wpkh(pub84, "ltc"),
        }
    elif coin_type == 145:  # Bitcoin Cash
        addr = _pub_to_p2pkh(pub44, b"\x00")
        return {"address": addr}
    elif coin_type == 236:  # Bitcoin SV
        addr = _pub_to_p2pkh(pub44, b"\x00")
        return {"address": addr}
    elif coin_type == 714:  # Binance Chain
        addr = _pub_to_p2pkh(pub44, b"\xB0")
        return {"address": addr}
    return {}


def derive_eth(seed, account=0, address_index=0):
    _, _, pub = _derive_path(seed, f"m/44'/60'/{account}'/0/{address_index}")
    ser = _point_ser(pub, False)
    from Crypto.Hash import keccak_256
    k = keccak_256.new()
    k.update(ser[1:])
    return {"address": "0x" + k.digest()[-20:].hex()}


def derive_sol(mnemonic, account=0):
    import nacl.bindings
    from nacl import encoding

    seed_bytes = mnemonic_to_seed(mnemonic)
    k, c, _ = _seed_to_master(seed_bytes)
    purpose = 44 + 0x80000000
    k, c, _ = _bip32_ckd(k, c, purpose)
    coin = 501 + 0x80000000
    k, c, _ = _bip32_ckd(k, c, coin)
    acc = account + 0x80000000
    k, c, _ = _bip32_ckd(k, c, acc)
    k, c, _ = _bip32_ckd(k, c, 0)
    k, c, _ = _bip32_ckd(k, c, 0)

    seed_32 = _int_to(k, 32)
    seed_32 = hashlib.sha512(seed_32).digest()[:32]

    sk = nacl.bindings.crypto_sign_seed_keypair(seed_32)
    pk = sk[1]
    return {"address": encoding.Base58Encoder.encode(pk).decode()}


COIN_CONFIGS = {
    "btc": {"label": "Bitcoin", "coin_type": 0},
    "ltc": {"label": "Litecoin", "coin_type": 2},
    "bch": {"label": "Bitcoin Cash", "coin_type": 145},
    "bsv": {"label": "Bitcoin SV", "coin_type": 236},
    "bnb": {"label": "Binance Chain", "coin_type": 714},
    "eth": {"label": "Ethereum", "coin_type": 60},
    "sol": {"label": "Solana", "coin_type": 501},
}


def derive_coin(mnemonic, coin_key, account=0, address_index=0):
    seed = mnemonic_to_seed(mnemonic)
    if coin_key == "eth":
        return derive_eth(seed, account, address_index)
    elif coin_key == "sol":
        return derive_sol(mnemonic, account)
    elif coin_key in ("btc", "ltc", "bch", "bsv", "bnb"):
        return derive_btc_like(seed, COIN_CONFIGS[coin_key]["coin_type"], account, address_index)
    return {}


def derive_all(mnemonic, account=0, address_index=0):
    results = {}
    for coin_key in COIN_CONFIGS:
        try:
            results[coin_key] = derive_coin(mnemonic, coin_key, account, address_index)
        except Exception as e:
            results[coin_key] = {"error": str(e)}
    return results