import json
import os
import sys

import core


def get_data_processing_choice_input():
    while True:
        print("Choose an option:")
        print("1. Process a single wallet")
        print("2. Get top performers for a wallet")
        print("0. Exit")

        user_input = input('Your choice: ')

        if user_input == '1':
            print("Selected option 1")
            return 1
        elif user_input == '2':
            print("Selected option 2")
            return 2
        elif user_input == '0':
            exit_app()
        else:
            print("Invalid choice. Please select again.")


def get_address(address_type):
    print("\n")
    print(f"Please enter a {address_type} address for a token you wish to analyze.")

    address = input(f"Input the {address_type} address: ").strip()

    # Validate input and identify blockchain
    if not address:
        print("No address provided.")
        exit_app()

    return address


def print_decorative_message(message):
    border = "*" * (len(message) + 4)
    print(border)
    print(f"* {message} *")
    print(border)


def print_token_details(token):
    print("")
    print("Token identified.")
    print("")
    print("Chain: " + token['chainId'])
    print("Dex: " + token['dexId'])
    print("URL: " + token['url'])
    print("Name: " + token['baseToken']['name'])
    print("Ticker: " + token['baseToken']['symbol'])
    print("CA: " + token['baseToken']['address'])


def process_query(address):
    token, error = core.fetch_data(address)
    return token, error


def save_data_to_json(data, path, filename):
    directory = os.path.join(path, filename)
    os.makedirs(path, exist_ok=True)  # Ensure the directory exists, create if not
    with open(directory, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Data successfully saved to {directory}")


def load_data_from_json(path, filename):
    directory = os.path.join(path, filename)
    if os.path.exists(directory):
        with open(directory, 'r') as f:
            return json.load(f)
    else:
        return None


def exit_app():
    print("Exiting Walko ...")
    sys.exit()
