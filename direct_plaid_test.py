import os
import django
import plaid
import json

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'overseenbudget.settings')
django.setup()

# Import Django models after setting up Django
from django.conf import settings
from home.models import PlaidItem

# Initialize Plaid client
plaid_client = plaid.Client(
    client_id=settings.PLAID_CLIENT_ID,
    secret=settings.PLAID_SECRET,
    environment=settings.PLAID_ENV
)

# Get the most recent Plaid item
plaid_items = PlaidItem.objects.all().order_by('-id')
if plaid_items.exists():
    item = plaid_items.first()
    print(f"Testing with Plaid Item ID: {item.id}")
    print(f"Access Token: {item.access_token}")
    print(f"Institution: {item.institution_name}")
    
    # Try to get accounts using the direct API call
    try:
        print("\nTrying to get accounts using direct API call:")
        response = plaid_client.post('/accounts/get', {
            'access_token': item.access_token
        })
        print(f"Response: {response}")
        
        # Check if response is a dictionary with 'accounts' key
        if isinstance(response, dict) and 'accounts' in response:
            accounts = response['accounts']
            print(f"\nFound {len(accounts)} accounts:")
            for account in accounts:
                print(f"Account: {account['name']} ({account['type']}) - Balance: {account['balances']['current']}")
        else:
            print(f"No accounts found in response. Response keys: {response.keys() if isinstance(response, dict) else 'Not a dictionary'}")
    
    except Exception as e:
        print(f"Error getting accounts: {str(e)}")
    
    # Try to get transactions using the direct API call
    try:
        print("\nTrying to get transactions using direct API call:")
        response = plaid_client.post('/transactions/get', {
            'access_token': item.access_token,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'options': {
                'count': 10
            }
        })
        print(f"Response: {response}")
        
        # Check if response is a dictionary with 'transactions' key
        if isinstance(response, dict) and 'transactions' in response:
            transactions = response['transactions']
            print(f"\nFound {len(transactions)} transactions:")
            for transaction in transactions[:5]:  # Just print first 5
                print(f"Transaction: {transaction['name']} ({transaction['amount']})")
        else:
            print(f"No transactions found in response. Response keys: {response.keys() if isinstance(response, dict) else 'Not a dictionary'}")
    
    except Exception as e:
        print(f"Error getting transactions: {str(e)}")
else:
    print("No Plaid items found in the database.") 