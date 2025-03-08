import datetime
import sys
import json
import os
import requests

def extract_transaction_data(json_data):
    data = json.loads(json_data)

    transactions = data['data']['transactions']

    def extract_txn(txn):
        txn['amount'] = txn['amount'] / 1000.0
        # Remove unnecessary fields
        fields_to_remove = [
            'flag_color', 'flag_name', 'account_id', 'payee_id', 'category_id',
            'transfer_account_id', 'transfer_transaction_id', 'matched_transaction_id',
            'import_id', 'import_payee_name', 'import_payee_name_original',
            'debt_transaction_type', 'subtransactions'
        ]
        for field in fields_to_remove:
            txn.pop(field, None)  # Remove field if it exists, do nothing if it doesn't

        return txn
    

    
    return [extract_txn(txn) for txn in transactions]

def get_and_extract_transaction_data(api_url, bearer_token, budget_id, since_date):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        url = f"{api_url}/budgets/{budget_id}/transactions"
        response = requests.get(url, headers=headers, params={'since_date': since_date})
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
ynab_token = os.environ['YNAB_TOKEN']

budget_id = sys.argv[1]
since_date = sys.argv[2]
# Example of reading the token from a file (recommended):
with open(".token", "r") as f:
	bearer_token = f.read().strip()

extracted_data = get_and_extract_transaction_data(ynab_api, bearer_token, budget_id, since_date)

# Print CSV header

for item in extracted_data:
    try:
        print(json.dumps(item))
    except BrokenPipeError:
        pass