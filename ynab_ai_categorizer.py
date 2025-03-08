import anthropic
import argparse
import datetime
import json
import os
import requests
import sys

def get_allowed_categories(api_url, bearer_token, budget_id):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    url = f"{api_url}/budgets/{budget_id}/categories"
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    json_data = response.text
    data = json.loads(json_data)
    category_names = []
    for group in data['data']['category_groups']:
        for category in group['categories']:
            category_names.append(category['name'])
    return category_names


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

    url = f"{api_url}/budgets/{budget_id}/transactions"
    response = requests.get(url, headers=headers, params={'since_date': since_date})
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    json_data = response.text
    return extract_transaction_data(json_data)

# Example usage:
ynab_api = "https://api.ynab.com/v1"
ynab_token = os.environ['YNAB_TOKEN']

def main():

    parser = argparse.ArgumentParser(description='Process YNAB transactions')
    parser.add_argument('--budget-id', required=True, help='YNAB budget ID')
    parser.add_argument('--since-date', required=True, help='Get transactions since this date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Run without making any changes')
    parser.add_argument('--max-output-tokens', type=int, default=1000, help='Maximum number of output tokens')
    parser.add_argument('--model', default='claude-3-5-haiku-20241022', help='Anthropic model to use')
    parser.add_argument('--output-file', default='/dev/null', help='Output file path')
    args = parser.parse_args()

    budget_id = args.budget_id
    since_date = args.since_date
    max_tokens = args.max_output_tokens
    model = args.model

    categories = get_allowed_categories(ynab_api, ynab_token, budget_id)
    transactions = get_and_extract_transaction_data(ynab_api, ynab_token, budget_id, since_date)

    by_id = { transaction['id']: transaction for transaction in transactions}

    # Split transactions into approved and unapproved lists
    approved = []
    unapproved = []
    
    for txn in transactions:
        is_approved = txn.pop('approved')  # Remove and get the approved field
        
        # Create details dict without id and category_name
        details = txn.copy()
        id = details.pop('id')
        category = details.pop('category_name')
        
        if is_approved:
            txn_output = {
                'id': id,
                'details': details,
                'category': category, 
            }
            approved.append(txn_output)
        else:
            txn_output = {
                'id': txn['id'], 
                'details': details,
                'proposed_category': category,
            }
            unapproved.append(txn_output)

    prompt = rf'''You are going to assign categories to personal financial transactions. The following are the allowed categories:
```
{"\n".join(categories)}
```

Here are some example categorized transactions:
```
{"\n".join(json.dumps(x) for x in approved)}
```

For each of the following unapproved transactions, print a single json object containing the fields id, category, and reason. "category" should be the most specific category that transaction would fit in. "reason" should be a very short justification for the selected category. There may be an existing proposed category provided, this is just a guess based on having previously seen the same payee name. Feel free to override it if you think it's likely incorrect, for example if you think this transaction is materially different from the previous transaction with that payee, or if the payee sells a wide variety of possible goods, like Amazon. Print no other output.
```
{"\n".join(json.dumps(x) for x in unapproved)}
```
'''

    # Get token count from Anthropic API
    client = anthropic.Anthropic()

    print(prompt)
    messages = [
        {"role": "user", "content": prompt}
    ]
    token_count = client.messages.count_tokens(
        model=model,
        messages=messages,
        )
    print(f"Prompt is {token_count.input_tokens} input tokens")
    if not args.dry_run:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            )
        print(response)

        responses = response.content[0].text.split("\n")
        with open(args.output_file, 'w') as f:
            for response in responses:
                try:
                    data = json.loads(response)
                    id = data['id']
                    txn = by_id[id]
                    output = {
                        'id': id,
                        'details': txn,
                        'ynab_category': txn['category_name'],
                        'ai_category': data['category'],
                        'ai_reason': data['reason'],
                    }
                    print(json.dumps(output))
                    print(json.dumps(output), file=f)
                except json.JSONDecodeError:
                    print(f"Failed to parse response line: {response}", file=sys.stderr)
                except KeyError as e:
                    print(f"Missing required field in response: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"Unexpected error processing response: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()