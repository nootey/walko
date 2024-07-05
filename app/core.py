import datetime
import inspect
import json
import os
import time

import requests
from ratelimit import sleep_and_retry, limits
from tqdm import tqdm

public_api_url = "https://docs-demo.solana-mainnet.quiknode.pro/"
headers = {
    "Content-Type": "application/json"
}

# Rate limit constants
MAX_REQUESTS_PER_RPC = 10
MAX_CONCURRENT_CONNECTIONS = 5
CONNECTION_RATE_LIMIT = 10


@sleep_and_retry
@limits(calls=MAX_REQUESTS_PER_RPC, period=CONNECTION_RATE_LIMIT)
def check_limit():
    return


def fetch_data(address):
    url = f"https://api.dexscreener.com/latest/dex/search/?q={address}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'pairs' in data and isinstance(data['pairs'], list) and len(data['pairs']) > 0:
                return data['pairs'][0], None  # Return the first entry and no error
            else:
                return None, "No pairs found in the response"
        else:
            return None, f"Error: {response.status_code} - {response.reason}"
    except requests.exceptions.RequestException as e:
        return None, f"Request error: {e}"


def get_interacting_wallets_sol(token_address):
    check_limit()
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [token_address]
    }

    try:

        response = requests.post(public_api_url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            data = response.json()
            return data["result"]["value"], None

        else:
            return None, f"Error: {response.status_code} - {response.reason}"
    except requests.exceptions.RequestException as e:
        return None, f"Request error: {e}"


def get_transaction_signatures(address):

    current_function_name = inspect.currentframe().f_code.co_name
    all_signatures = []
    before = None

    try:
        while True:
            check_limit()
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    address,
                    {"limit": 1000, "before": before} if before else {"limit": 1000}
                ]
            }

            response = requests.post(public_api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    return None, f"Error for function {current_function_name}: {data['error']}"

                filtered_results = [tx for tx in data["result"] if
                                    tx["err"] is None and tx["confirmationStatus"] == "finalized"]
                all_signatures.extend(filtered_results)

                if len(data["result"]) < 1000:
                    break
                print(data["result"][-1]["signature"])
                before = data["result"][-1]["signature"]
            else:
                return None, f"Error for function {current_function_name}: {response.status_code} - {response.reason}"

        return all_signatures, None

    except requests.exceptions.RequestException as e:
        return None, f"Request error for function {current_function_name}: {e}"


def get_transaction_details(signature):

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }
    current_function_name = inspect.currentframe().f_code.co_name
    max_retries = 3

    for attempt in range(max_retries):
        check_limit()
        try:
            response = requests.post(public_api_url, headers=headers, data=json.dumps(payload))

            if response.status_code == 200:
                data = response.json()
                return data.get("result"), None
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    check_limit()
                else:
                    return None, f"Error for function {current_function_name}: {response.status_code} - {response.reason} after {max_retries} attempts"
            else:
                return None, f"Error for function {current_function_name}: {response.status_code} - {response.reason}"
        except requests.exceptions.RequestException as e:
            return None, f"Request error for function {current_function_name}: {e}"


def get_token_price(token_address, timestamp):
    check_limit()

    if token_address == "":
        return None

    dt_object = datetime.datetime.fromtimestamp(timestamp)
    date_string = dt_object.strftime('%d-%m-%Y')

    time_from = timestamp - 30  # 30 sec before
    time_to = timestamp + 30  # 30 sec after

    json_file_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'birdeye.json')
    with open(json_file_path) as f:
        config = json.load(f)
    api_key = config.get('api_key')

    url = f"https://public-api.birdeye.so/defi/history_price?address=" \
          f"{token_address}&address_type=token&type=1m&time_from=" \
          f"{time_from}&time_to={time_to}"

    api_headers = {"X-API-KEY": api_key}

    try:
        response = requests.get(url, headers=api_headers)
        response.raise_for_status()  # Raise an error for bad HTTP status codes
        data = response.json()

        # Check if 'items' contains data
        if data.get('success') and 'items' in data.get('data', {}):
            items = data['data']['items']
            if items:
                # Assuming the first item is the relevant one
                price_info = items[0]
                if 'value' in price_info:
                    price = price_info['value']
                    return price
                else:
                    return None
            else:
                return None
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

    return None  # Return None if data retrieval fails


def get_token_transfers(meta, wallet_address):
    pre_balances = {balance['accountIndex']: balance for balance in meta.get('preTokenBalances', [])}
    post_balances = {balance['accountIndex']: balance for balance in meta.get('postTokenBalances', [])}

    all_account_indexes = set(pre_balances.keys()).union(set(post_balances.keys()))

    token_transfers = []

    for index in all_account_indexes:
        pre_balance = pre_balances.get(index)
        post_balance = post_balances.get(index)

        # Check if the owner matches the provided wallet_address
        pre_owner = pre_balance.get('owner') if pre_balance else None
        post_owner = post_balance.get('owner') if post_balance else None

        if pre_owner == wallet_address or post_owner == wallet_address:
            token_transfer = {
                'accountIndex': index,
                'preBalance': pre_balance,
                'postBalance': post_balance
            }
            token_transfers.append(token_transfer)

    return token_transfers


def process_transaction(transaction, wallet_address, minted_tokens):
    stats_list = []  # List to store stats dictionaries
    meta = transaction.get('meta', {})

    if not meta:
        return []

    token_transfers = get_token_transfers(meta, wallet_address)
    if len(token_transfers) == 0:
        return []

    # Check for potential mints
    inner_instructions = meta.get('innerInstructions', [])
    if inner_instructions:
        for inner_instruction in inner_instructions:
            instructions = inner_instruction.get('instructions', [])
            if instructions:
                for instruction in instructions:
                    parsed = instruction.get('parsed', {})
                    if parsed and "info" in parsed:
                        info = parsed["info"]
                        if info and "authority" in info:
                            authority = info["authority"]
                            if wallet_address == authority and "mint" in info and "tokenAmount" in info:
                                token_amount = info["tokenAmount"]
                                token = info["mint"]
                                price_then = get_token_price(token, transaction['blockTime'])
                                if price_then is None:
                                    price_then = 0.0
                                if token not in minted_tokens:
                                    minted_tokens.append(token)

    for token_transfer in token_transfers:

        pre_balance = token_transfer.get("preBalance", {})
        post_balance = token_transfer.get("postBalance", {})

        if not pre_balance and not post_balance:
            continue

        pre_token_amount = pre_balance.get("uiTokenAmount") if isinstance(pre_balance, dict) else None
        post_token_amount = post_balance.get("uiTokenAmount") if isinstance(post_balance, dict) else None

        pre_amount = 0.0
        post_amount = 0.0
        token = ""
        price = 0.0

        if post_token_amount and post_token_amount['uiAmount'] is not None:
            post_amount = float(post_token_amount['uiAmount'])
            token = post_balance["mint"]
            price = get_token_price(token, transaction['blockTime'])
            if price is None:
                price = 0.0

        if pre_token_amount and pre_token_amount['uiAmount'] is not None:
            token = pre_balance["mint"]
            pre = pre_balance['uiTokenAmount']
            if pre == "0":
                pre_amount = 0.0
            else:
                if pre['uiAmount'] is None:
                    continue
            pre_amount = float(pre['uiAmount'])

        difference = abs(pre_amount - post_amount)

        if post_amount > pre_amount:
            transaction_type = "buy"
            multiplier = -1
        else:
            transaction_type = "sell"
            multiplier = 1

        stats = {
            "token": token,
            "type": transaction_type,
            "pre_amount": pre_amount,
            "post_amount": post_amount,
            "amount_difference": difference,
            "price_usd": price,
            "value_usd": multiplier * difference * price,
            "timestamp": transaction['blockTime'],
        }
        stats_list.append(stats)

    return stats_list


def calculate_performance(data, wallet_address):
    results = {}
    current_timestamp = int(time.time())
    unique_tokens = 0
    wins = 0

    for txn in tqdm(data, desc=f"Calculating performance for: {wallet_address}"):
        for stat in txn["stats"]:
            token = stat["token"]
            if token == "":
                continue

            amount_difference = stat["amount_difference"]
            price_usd = stat["price_usd"]
            timestamp = stat["timestamp"]
            txn_type = stat["type"]

            # If price_usd is 0.0, get the price
            if price_usd == 0.0:
                price_usd = get_token_price(token, timestamp)

            if price_usd is None:
                continue

            # Calculate value_usd
            mp = 1
            if txn_type == "buy":
                mp = -1

            value_usd = (amount_difference * price_usd) * mp

            # Append the processed data to the dictionary
            if token not in results:
                results[token] = {"transactions": [], "total_value": 0}
                unique_tokens += 1

            results[token]["transactions"].append({
                "amount_difference": amount_difference,
                "price_usd": price_usd,
                "value_usd": value_usd,
                "timestamp": datetime.datetime.fromtimestamp(timestamp).isoformat()  # Convert to readable date
            })
            results[token]["total_value"] += value_usd

    total_wallet_value = 0.0
    total_wallet_value_current = 0.0

    # Calculate current prices and current values
    for token, info in results.items():
        current_price_usd = get_token_price(token, current_timestamp)
        if current_price_usd is None:
            current_price_usd = 0.0

        total_value_current = 0

        for txn in info["transactions"]:
            current_value_usd = txn["amount_difference"] * current_price_usd
            txn["current_price_usd"] = current_price_usd
            txn["current_value_usd"] = current_value_usd
            total_value_current += current_value_usd

        info["total_value_current"] = total_value_current
        if info["total_value"] > 0:
            wins += 1

        total_wallet_value += info["total_value"]
        total_wallet_value_current += total_value_current

    winrate = wins / unique_tokens if unique_tokens > 0 else 0
    results["unique_tokens"] = unique_tokens
    results["winrate"] = winrate
    results["value_at_transaction"] = total_wallet_value
    results["current_value"] = total_wallet_value_current

    return results
