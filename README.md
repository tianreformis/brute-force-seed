# Zyra Wallet Seed Phrase Balance Checker

A Python tool to generate BIP39 mnemonic seed phrases, derive cryptocurrency wallets, and check balances across multiple blockchains.

## Supported Coins

| Coin | Address Types |
|------|---------------|
| Bitcoin (BTC) | P2PKH, P2SH (Nested SegWit), P2WKH (Native SegWit) |
| Litecoin (LTC) | P2PKH, P2SH, P2WKH |
| Ethereum (ETH) | BIP44 address |
| Solana (SOL) | Ed25519 address |
| Bitcoin Cash (BCH) | Legacy address |
| Bitcoin SV (BSV) | Legacy address |
| Binance Chain (BNB) | BEP2 address |

## Requirements

- Python 3.10+
- pip

## Installation

```bash
# Clone or download the project, then:
pip install -r requirements.txt
```

## Usage

### Generate Mode (random brute-force)

Continuously generates random seed phrases and checks their balances. Uses a deterministic counter-based state to ensure no repeats. Resumes automatically from where it left off.

```bash
python main.py generate
```

```bash
# With specific coins and verbose output
python main.py generate --coins btc eth --verbose

# Save found wallets to file
python main.py generate --save

# Reset the generation state to start fresh
python main.py generate --reset-state

# 24-word phrases (256-bit entropy)
python main.py generate --bits 256

# Delay between checks (rate limiting)
python main.py generate --delay 1
```

### Check Mode (single mnemonic)

```bash
python main.py check -m "seed phrase words here..."
```

```bash
# Check specific coins only
python main.py check -m "your seed phrase" --coins btc eth sol

# Save result if balance found
python main.py check -m "seed phrase" --save
```

### Check Mode (batch from file)

```bash
python main.py check -f seeds.txt
```

File should contain one mnemonic per line.

### API Keys (optional, for higher rate limits)

```bash
python main.py generate --etherscan-key YOUR_KEY --solscan-key YOUR_KEY
```

Default balance checkers work without API keys but have rate limits.

## Project Structure

```
├── main.py              # CLI entry point
├── requirements.txt     # Python dependencies
├── data/
│   ├── state.json       # Generation state (auto-created)
│   └── wordlist_english.txt
├── results/             # Found wallets saved here (auto-created)
│   ├── found_wallets.json
│   ├── found_wallets.txt
│   └── checked_log.txt
└── src/
    ├── mnemonic.py      # BIP39 generation & validation
    ├── wallet.py        # HD wallet derivation (BIP44/49/84)
    ├── balance_checker.py
    ├── state.py         # Persistent counter-based state
    └── logger.py
```

## How It Works

1. **Entropy Generation**: A random master seed is generated once. Each subsequent wallet uses `SHA256(master_seed + counter)` as entropy — guaranteeing no repeats.
2. **Mnemonic**: Entropy is converted to a BIP39 mnemonic phrase with checksum.
3. **Wallet Derivation**: From the mnemonic seed, HD wallets are derived using BIP44, BIP49, and BIP84 paths for UTXO coins, and BIP44 for ETH/SOL.
4. **Balance Check**: Public APIs (Blockchain.info, Etherscan, BlockCypher, Solana RPC) are queried for each address.
5. **State Persistence**: Counter and master seed are saved to `data/state.json`. Resume anytime without repeating.