import os
import json

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def log_found(mnemonic, balances, wallet_addrs):
    ensure_results_dir()
    filepath = os.path.join(RESULTS_DIR, "found_wallets.txt")
    with open(filepath, "a") as f:
        f.write(f"\n=== WALLET FOUND ===\n")
        f.write(f"Mnemonic: {mnemonic}\n")
        for coin, addrs in wallet_addrs.items():
            bal = balances.get(coin, {})
            bal_str = bal.get("balance", "unknown")
            f.write(f"  {coin.upper()}: {addrs} | Balance: {bal_str}\n")
        f.write("=" * 50 + "\n")


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