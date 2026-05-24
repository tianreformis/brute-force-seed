import os
import json
import time

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def _has_positive_balance(balances):
    for coin, bal in balances.items():
        b = bal.get("balance", 0)
        if isinstance(b, (int, float)) and b > 0:
            return True
        if isinstance(b, str):
            try:
                if float(b) > 0:
                    return True
            except ValueError:
                pass
    return False


def log_found(mnemonic, balances, wallet_addrs):
    ensure_results_dir()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    entry = {
        "timestamp": ts,
        "mnemonic": mnemonic,
        "balances": balances,
        "wallets": wallet_addrs,
    }

    json_path = os.path.join(RESULTS_DIR, "found_wallets.json")
    existing = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, json.decoder.JSONDecodeError):
            existing = []
    existing.append(entry)
    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2)

    txt_path = os.path.join(RESULTS_DIR, "found_wallets.txt")
    with open(txt_path, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"FOUND: {ts}\n")
        f.write(f"Mnemonic: {mnemonic}\n\n")
        for coin, addrs in wallet_addrs.items():
            bal = balances.get(coin, {})
            bal_str = bal.get("balance", "?")
            tx_str = bal.get("tx_count", "?")
            if isinstance(addrs, dict):
                for addr_type, addr_val in addrs.items():
                    if addr_val:
                        f.write(f"  {coin.upper()} [{addr_type}]: {addr_val}\n")
            else:
                f.write(f"  {coin.upper()}: {addrs}\n")
            f.write(f"  {coin.upper()} Balance: {bal_str} | TX: {tx_str}\n")
        f.write(f"{'='*60}\n")


def log_checked(mnemonic, balances, wallet_addrs):
    ensure_results_dir()
    filepath = os.path.join(RESULTS_DIR, "checked_log.txt")
    with open(filepath, "a") as f:
        f.write(f"Mnemonic: {mnemonic[:20]}...\n")
        for coin, addrs in wallet_addrs.items():
            bal = balances.get(coin, {})
            bal_str = bal.get("balance", "?")
            f.write(f"  {coin}: {bal_str}\n")
        f.write("-" * 30 + "\n")