import logging
import os
import sys
from datetime import datetime

from tqdm import tqdm

import core
import helpers
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def calculate_wallet_performance(wallet_address, save_type):

    current_date = datetime.now().strftime('%Y-%m-%d')
    processed_save_path = os.path.join(os.path.dirname(__file__), '', '../data', save_type, current_date, 'processed')
    results_save_path = os.path.join(os.path.dirname(__file__), '', '../data', save_type, current_date, 'results')
    # Ensure directories exist; create if they don't
    os.makedirs(processed_save_path, exist_ok=True)
    os.makedirs(results_save_path, exist_ok=True)

    # Gather processed data
    processed_transactions = []
    existing_data = helpers.load_data_from_json(processed_save_path, wallet_address)
    if existing_data:
        processed_transactions = existing_data
    else:
        signatures, err = core.get_transaction_signatures(wallet_address)
        if err is not None:
            print(err)
            raise Exception(err)

        minted_tokens = []
        for signature in tqdm(signatures, desc=f"Processing transaction signatures for address: {wallet_address}"):
            txn_hash = signature["signature"]
            transaction, err = core.get_transaction_details(txn_hash)
            if err is not None:
                print(err)
                raise Exception(err)

            result = core.process_transaction(transaction, wallet_address, minted_tokens)
            if len(result) > 0:
                result_list = {"txn_hash": txn_hash, "stats": result}
                processed_transactions.append(result_list)

        if len(processed_transactions) > 0:
            helpers.save_data_to_json(processed_transactions, processed_save_path, wallet_address)

    # Gather results
    results = []
    existing_results = helpers.load_data_from_json(results_save_path, wallet_address)
    if existing_results:
        results = existing_results
    else:
        results = core.calculate_performance(processed_transactions, wallet_address)
        if len(results) > 0:
            helpers.save_data_to_json(results, results_save_path, wallet_address)

    total_value = 0.0
    total_value_current = 0.0

    for token, info in results.items():
        # print(f"Token: {token}")
        # print(f"Total value at transaction time: {info['total_value']}")
        # print(f"Total current value: {info['total_value_current']}")
        total_value += info['total_value']
        total_value_current += info['total_value_current']
        # for txn in info["transactions"]:
        #     print(txn)

    print(f"PnL for wallet at transaction time: {format(total_value, '.2f')}$")
    print(f"PnL for wallet at current time: {format(total_value_current, '.2f')}$")


def get_top_performers(token_address):
    # Display token info
    with tqdm(total=1, desc="Processing query") as pbar:
        token, err = helpers.process_query(token_address)
        pbar.update(1)

    if err is not None:
        print(f"Error processing token address: {err}")
    else:
        helpers.print_token_details(token)
    print("\n")

    if token['chainId'] != "solana":
        print(f"Chain {token['chainId']} is currently not supported for wallet analysis!")
        sys.exit()

    # Get applicable wallets
    with tqdm(total=1, desc="Fetching wallets that interacted with the token") as pbar:
        wallets, err = core.get_interacting_wallets_sol(token_address)
        pbar.update(1)

    if err is not None:
        print(f"Error fetching wallets: {err}")
        sys.exit()

    return wallets


def main():
    try:
        print("\n")
        helpers.print_decorative_message("Welcome to Walko, a blockchain wallet analyzer!")
        print("\n")

        user_choice = helpers.get_data_processing_choice_input()

        if user_choice == 1:
            wallet_address = helpers.get_address("wallet")
            calculate_wallet_performance(wallet_address, "single")
        elif user_choice == 2:
            token_address = helpers.get_address("tokan")
            wallets = get_top_performers(token_address)
            for wallet in wallets:
                calculate_wallet_performance(wallet["address"], "multi")

        print("Exiting Walko ...")
        sys.exit()

    except Exception as e:
        logger.error(f'An error occurred: {e}', exc_info=True)


if __name__ == "__main__":
    main()
