import sys
import os
import argparse
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mnemonic import generate_mnemonic, mnemonic_to_seed, validate_mnemonic, load_wordlist
from src.wallet import derive_all, COIN_CONFIGS
from src.balance_checker import check_btc, check_eth, check_ltc, check_sol
from src.logger import log_found, log_checked

running = True

BALANCE_CHECKERS = {
    "btc": check_btc,
    "eth": check_eth,
    "ltc": check_ltc,
    "sol": check_sol,
}


def signal_handler(sig, frame):
    global running
    print("\n[!] Interrupted. Stopping...")
    running = False


def print_banner():
    print("=" * 60)
    print("  Zyra Wallet Seed Phrase Balance Checker - Python Edition")
    print("  Supports: BTC | ETH | LTC | SOL | BCH | BNB | BSV")
    print("=" * 60)


def process_mnemonic(mnemonic, checkers, verbose=False):
    seed = mnemonic_to_seed(mnemonic)
    wallets = derive_all(mnemonic)
    balances = {}

    if verbose:
        print(f"\n[+] Mnemonic: {mnemonic}")
        for coin_key, addrs in wallets.items():
            if isinstance(addrs, dict):
                addr_str = "; ".join(f"{k}={v}" for k, v in addrs.items() if v)
                print(f"    {coin_key.upper()}: {addr_str}")

    for coin_key, checker in checkers.items():
        coin_wallets = wallets.get(coin_key, {})
        if not coin_wallets or "error" in coin_wallets:
            continue
        if isinstance(coin_wallets, dict):
            check_addr = None
            for addr_type in ("p2wkh", "p2sh", "p2pkh", "address"):
                if coin_wallets.get(addr_type):
                    check_addr = coin_wallets[addr_type]
                    break
            if check_addr:
                bal = checker(check_addr)
                balances[coin_key] = bal
                if verbose:
                    amt = bal.get("balance", "?")
                    print(f"    {coin_key.upper()} balance: {amt}")

    return wallets, balances


def generate_loop(bits, delay, checkers, verbose, save_found):
    global running
    checked = 0
    while running:
        try:
            mnemonic, _ = generate_mnemonic(bits)
            checked += 1
            wallets, balances = process_mnemonic(mnemonic, checkers, verbose)

            has_funds = False
            for coin, bal in balances.items():
                b = bal.get("balance", 0)
                if isinstance(b, (int, float)) and b > 0:
                    has_funds = True
                elif isinstance(b, str):
                    try:
                        if float(b) > 0:
                            has_funds = True
                    except ValueError:
                        pass

            if has_funds:
                print(f"\n*** FUNDS FOUND! ***")
                print(f"Mnemonic: {mnemonic}")
                for coin, bal in balances.items():
                    print(f"  {coin.upper()}: {bal.get('balance', '?')}")
                if save_found:
                    log_found(mnemonic, balances, wallets)

            if verbose:
                log_checked(mnemonic, balances, wallets)
            else:
                if checked % 100 == 0:
                    print(f"[*] Checked {checked} wallets...", end="\r")

            if delay > 0:
                time.sleep(delay)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[!] Error: {e}")
            continue

    print(f"\n[*] Done. Checked {checked} wallets.")


def single_check(mnemonic, checkers, verbose, save_found):
    if not validate_mnemonic(mnemonic):
        print("[!] Invalid mnemonic phrase")
        return

    wallets, balances = process_mnemonic(mnemonic, checkers, verbose=verbose)

    print(f"\nMnemonic: {mnemonic}")
    print(f"\n--- Derived Wallets ---")
    for coin, addrs in wallets.items():
        label = COIN_CONFIGS.get(coin, {}).get("label", coin.upper())
        if isinstance(addrs, dict) and "error" not in addrs:
            addr_str = " | ".join(f"{k}: {v}" for k, v in addrs.items() if v)
            print(f"  {label} ({coin.upper()}): {addr_str}")
        elif isinstance(addrs, dict) and "error" in addrs:
            print(f"  {label} ({coin.upper()}): ERROR - {addrs['error']}")
        else:
            print(f"  {label} ({coin.upper()}): {addrs}")

    print(f"\n--- Balances ---")
    has_funds = False
    for coin, bal in balances.items():
        label = COIN_CONFIGS.get(coin, {}).get("label", coin.upper())
        b = bal.get("balance", "N/A")
        tx = bal.get("tx_count", "N/A")
        print(f"  {label} ({coin.upper()}): {b} | TX: {tx}")
        if isinstance(b, (int, float)) and b > 0:
            has_funds = True

    if has_funds:
        print(f"\n*** FUNDS FOUND! ***")
        if save_found:
            log_found(mnemonic, balances, wallets)


def load_mnemonics_from_file(filepath):
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Zyra Wallet Seed Phrase Balance Checker"
    )
    parser.add_argument(
        "mode", nargs="?", choices=["generate", "check"],
        default="generate",
        help="Mode: generate random mnemonics or check an existing one"
    )
    parser.add_argument("-m", "--mnemonic", help="BIP39 mnemonic to check")
    parser.add_argument(
        "-f", "--file", help="File containing mnemonics (one per line)"
    )
    parser.add_argument(
        "--bits", type=int, default=128,
        choices=[128, 160, 192, 224, 256],
        help="Entropy bits (default: 128 = 12 words)"
    )
    parser.add_argument(
        "-c", "--coins", nargs="+",
        default=["btc", "eth", "ltc", "sol"],
        choices=["btc", "eth", "ltc", "sol", "bch", "bsv", "bnb"],
        help="Coins to check (default: btc eth ltc sol)"
    )
    parser.add_argument("--delay", type=float, default=0, help="Delay between checks (seconds)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--etherscan-key", help="Etherscan API key")
    parser.add_argument("--solscan-key", help="Solscan API key")

    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)

    print_banner()

    from src.balance_checker import set_api_key
    if args.etherscan_key:
        set_api_key("etherscan", args.etherscan_key)
    if args.solscan_key:
        set_api_key("solscan", args.solscan_key)

    checkers = {}
    for coin in args.coins:
        if coin in BALANCE_CHECKERS:
            checkers[coin] = BALANCE_CHECKERS[coin]
        else:
            print(f"[!] No balance checker for {coin}, skipping balance check")

    if args.file:
        mnemonics = load_mnemonics_from_file(args.file)
        print(f"[*] Loaded {len(mnemonics)} mnemonics from {args.file}")
        for mnemonic in mnemonics:
            if not running:
                break
            single_check(mnemonic, checkers, verbose=True, save_found=args.save)
            if args.delay > 0:
                time.sleep(args.delay)
    elif args.mode == "check" and args.mnemonic:
        single_check(args.mnemonic, checkers, verbose=True, save_found=args.save)
    elif args.mode == "generate":
        print(f"[*] Generating wallets with {args.bits}-bit entropy...")
        print(f"[*] Checking: {', '.join(checkers.keys())}")
        print("[*] Press Ctrl+C to stop\n")
        generate_loop(args.bits, args.delay, checkers, args.verbose, args.save)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()