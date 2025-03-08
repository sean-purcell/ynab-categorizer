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

transactions = get_and_extract_transaction_data(ynab_api, ynab_token, budget_id, since_date)

# Split transactions into approved and unapproved lists
approved = []
unapproved = []

for txn in transactions:
    is_approved = txn.pop('approved')  # Remove and get the approved field
    if is_approved:
        approved.append(txn)
    else:
        unapproved.append(txn)

for item in approved:
    try:
        # Create a copy of the item without id and category_name
        details = item.copy()
        details.pop('id')
        details.pop('category_name')
        
        txn_output = {
            'id': item['id'],
            'details': details,
            'category_name': item['category_name']
        }
        print(json.dumps(txn_output))
    except BrokenPipeError:
        pass

print("Unapproved:")

for item in unapproved:
    try:
        # Create a copy of the item without id
        details = item.copy()
        details.pop('id')
        details.pop('category_name')
    
        txn_output = {
            'id': item['id'],
            'details': details
        }
        print(json.dumps(txn_output))
    except BrokenPipeError:
        pass

