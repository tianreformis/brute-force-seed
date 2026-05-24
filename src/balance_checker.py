import requests
import json
import time
from functools import wraps

API_KEYS = {
    "etherscan": None,
    "blockcypher": None,
    "solscan": None,
}


def set_api_key(service, key):
    API_KEYS[service] = key


def rate_limit(delay=1.0):
    last_call = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < delay:
                time.sleep(delay - elapsed)
            result = func(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapper
    return decorator


@rate_limit(delay=0.5)
def check_btc_blockchain(address):
    url = f"https://blockchain.info/balance?active={address}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            addr_data = data.get(address, {})
            balance_sat = addr_data.get("final_balance", 0)
            tx_count = addr_data.get("n_tx", 0)
            return {
                "balance": balance_sat / 1e8,
                "tx_count": tx_count,
            }
    except Exception as e:
        return {"error": str(e)}
    return {"balance": 0, "tx_count": 0}


@rate_limit(delay=0.5)
def check_btc_blockcypher(address):
    url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "balance": data.get("final_balance", 0) / 1e8,
                "tx_count": data.get("final_n_tx", 0),
            }
    except Exception as e:
        return {"error": str(e)}
    return {"balance": 0, "tx_count": 0}


@rate_limit(delay=0.5)
def check_ltc_blockcypher(address):
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "balance": data.get("final_balance", 0) / 1e8,
                "tx_count": data.get("final_n_tx", 0),
            }
    except Exception as e:
        return {"error": str(e)}
    return {"balance": 0, "tx_count": 0}


@rate_limit(delay=0.5)
def check_eth_etherscan(address, api_key=None):
    api_key = api_key or API_KEYS.get("etherscan")
    if not api_key:
        api_key = "YourApiKeyToken"
    url = (
        f"https://api.etherscan.io/api"
        f"?module=account&action=balance"
        f"&address={address}&tag=latest&apikey={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                balance_wei = int(data.get("result", 0))
                return {"balance": balance_wei / 1e18}
    except Exception as e:
        return {"error": str(e)}
    return {"balance": 0}


@rate_limit(delay=0.5)
def check_eth_etherscan_tx(address, api_key=None):
    api_key = api_key or API_KEYS.get("etherscan")
    if not api_key:
        api_key = "YourApiKeyToken"
    url = (
        f"https://api.etherscan.io/api"
        f"?module=account&action=txlist"
        f"&address={address}&startblock=0&endblock=99999999"
        f"&sort=asc&apikey={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                return {"tx_count": len(data.get("result", []))}
            return {"tx_count": 0}
    except Exception:
        pass
    return {"tx_count": 0}


@rate_limit(delay=0.5)
def check_sol_solscan(address, api_key=None):
    headers = {}
    api_key = api_key or API_KEYS.get("solscan")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    url = f"https://api.solscan.io/account?address={address}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data:
                sol_balance = data["data"].get("solBalance", 0) / 1e9
                return {"balance": sol_balance}
    except Exception as e:
        return {"error": str(e)}
    return {"balance": 0}


@rate_limit(delay=0.5)
def check_sol_rpc(address, rpc_url="https://api.mainnet-beta.solana.com"):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address],
    }
    try:
        resp = requests.post(rpc_url, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data:
                lamports = data["result"]["value"]
                return {"balance": lamports / 1e9}
    except Exception as e:
        return {"error": str(e)}
    return {"balance": 0}


def check_btc(address):
    return check_btc_blockchain(address)


def check_eth(address):
    return check_eth_etherscan(address)


def check_ltc(address):
    return check_ltc_blockcypher(address)


def check_sol(address):
    return check_sol_rpc(address)