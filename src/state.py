import os
import json
import hashlib

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STATE_FILE = os.path.join(STATE_DIR, "state.json")


def ensure_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def load_state():
    ensure_dir()
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return None


def save_state(master_seed_hex, counter, total_checked):
    ensure_dir()
    with open(STATE_FILE, "w") as f:
        json.dump({
            "master_seed_hex": master_seed_hex,
            "counter": counter,
            "total_checked": total_checked,
        }, f, indent=2)


def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def init_state():
    state = load_state()
    if state is not None:
        return state["master_seed_hex"], state["counter"], state["total_checked"]
    master_seed = os.urandom(32)
    master_seed_hex = master_seed.hex()
    save_state(master_seed_hex, 0, 0)
    return master_seed_hex, 0, 0


def next_entropy(master_seed_hex, counter, bits=128):
    seed_bytes = bytes.fromhex(master_seed_hex)
    data = seed_bytes + str(counter).encode()
    h = hashlib.sha256(data).digest()
    entropy_size = bits // 8
    while len(h) < entropy_size:
        h += hashlib.sha256(h + data).digest()
    return h[:entropy_size]