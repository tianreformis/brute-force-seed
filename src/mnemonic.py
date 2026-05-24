import hashlib
import hmac
import os

BIP39_WORDLIST = None

def load_wordlist(path=None):
    global BIP39_WORDLIST
    if BIP39_WORDLIST:
        return BIP39_WORDLIST
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "wordlist_english.txt")
    with open(path, "r") as f:
        BIP39_WORDLIST = [w.strip() for w in f if w.strip()]
    return BIP39_WORDLIST


def bytes_to_bits(data):
    bits = ""
    for byte in data:
        bits += format(byte, "08b")
    return bits


def bits_to_bytes(bits):
    result = bytearray()
    for i in range(0, len(bits), 8):
        result.append(int(bits[i:i+8], 2))
    return bytes(result)


def generate_entropy(bits=128):
    if bits not in (128, 160, 192, 224, 256):
        raise ValueError("Entropy must be 128, 160, 192, 224, or 256 bits")
    return os.urandom(bits // 8)


def entropy_to_mnemonic(entropy, wordlist=None):
    if wordlist is None:
        wordlist = load_wordlist()
    if len(wordlist) != 2048:
        raise ValueError("Wordlist must contain exactly 2048 words")

    entropy_bits = bytes_to_bits(entropy)
    h = hashlib.sha256(entropy).digest()
    checksum_bits = bytes_to_bits(h)[:len(entropy) * 8 // 32]
    all_bits = entropy_bits + checksum_bits

    words = []
    for i in range(0, len(all_bits), 11):
        idx = int(all_bits[i:i+11], 2)
        words.append(wordlist[idx])
    return " ".join(words)


def generate_mnemonic(bits=128, wordlist_path=None):
    wordlist = load_wordlist(wordlist_path)
    entropy = generate_entropy(bits)
    return entropy_to_mnemonic(entropy, wordlist), entropy


def mnemonic_to_seed(mnemonic, passphrase=""):
    mnemonic_bytes = mnemonic.encode("utf-8")
    salt = ("mnemonic" + passphrase).encode("utf-8")
    stretched = hashlib.pbkdf2_hmac("sha512", mnemonic_bytes, salt, 2048)
    return stretched


def validate_mnemonic(mnemonic, wordlist=None):
    if wordlist is None:
        wordlist = load_wordlist()
    words = mnemonic.split()
    if len(words) not in (12, 15, 18, 21, 24):
        return False
    word_set = set(wordlist)
    if not all(w in word_set for w in words):
        return False

    indices = [wordlist.index(w) for w in words]
    bits = ""
    for idx in indices:
        bits += format(idx, "011b")

    checksum_size = len(words) // 3  # 12->4, 15->5, 18->6, 24->8
    entropy_bits = bits[:len(bits) - checksum_size]
    checksum_bits = bits[-checksum_size:]
    entropy = bits_to_bytes(entropy_bits)

    expected_checksum = bytes_to_bits(hashlib.sha256(entropy).digest())[:checksum_size]
    return checksum_bits == expected_checksum