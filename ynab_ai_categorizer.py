import datetime
import sys
import json
import os
import requests

def extract_transaction_data(json_data):
    data = json.loads(json_data)

    transactions = data['data']['transactions']

    def extract_txn(txn):
        txn['amount'] = txn['amount'] / 100.0

        return txn

def get_and_extract_transaction_data(api_url, bearer_token, budget_id, since_date):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        url = f"{api_url}/budgets/{budget_id}/transactions?since={since_date}""
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        json_data = response.text
        return extract_transaction_data(json_data)

    except requests.exceptions.RequestException as e:
        print(f"Error querying API: {e}")
        return []
    except json.JSONDecodeError:
        print("Invalid JSON response from API")
        return []
    except Exception as e: # Catch any other unexpected exceptions
        print(f"An unexpected error occurred: {e}")
        return []



# Example usage:
ynab_api = "https://api.ynab.com/v1"
ynab_token = os.environ['YNAB_API']

# Example of reading the token from a file (recommended):
with open(".token", "r") as f:
	bearer_token = f.read().strip()

if bearer_token: # Only proceed if the token was successfully read
    extracted_data = get_and_extract_transaction_data(api_url, bearer_token)

    if extracted_data:
        for item in extracted_data:
            print(item)
    else:
        print("No transaction data extracted.")
