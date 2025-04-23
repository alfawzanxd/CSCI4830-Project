import os
import django
import plaid
from datetime import datetime, timedelta

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

# Get the first Plaid item
plaid_items = PlaidItem.objects.all()
if plaid_items.exists():
    item = plaid_items.first()
    print(f"Testing with Plaid Item ID: {item.id}")
    print(f"Access Token: {item.access_token[:10]}...")
    print(f"Institution: {item.institution_name}")
    
    # Test accounts_get using plaid.api.accounts.get
    try:
        print("\nTesting plaid.api.accounts.get method:")
        response = plaid.api.accounts.get(access_token=item.access_token)
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")
        
        # Try to access accounts as dictionary
        if isinstance(response, dict) and 'accounts' in response:
            print("\nAccessing accounts as dictionary key:")
            accounts = response['accounts']
            print(f"Found {len(accounts)} accounts")
            for account in accounts:
                print(f"Account: {account['name']} ({account['type']})")
        else:
            print(f"Response is not a dictionary with 'accounts' key: {type(response)}")
            if isinstance(response, dict):
                print(f"Response keys: {response.keys()}")
    
    except Exception as e:
        print(f"Error testing plaid.api.accounts.get: {str(e)}")
    
    # Test transactions_get using plaid.api.transactions.get
    try:
        print("\nTesting plaid.api.transactions.get method:")
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        response = plaid.api.transactions.get(
            access_token=item.access_token,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")
        
        # Try to access transactions as dictionary
        if isinstance(response, dict) and 'transactions' in response:
            print("\nAccessing transactions as dictionary key:")
            transactions = response['transactions']
            print(f"Found {len(transactions)} transactions")
            for transaction in transactions[:5]:  # Just print first 5
                print(f"Transaction: {transaction['name']} ({transaction['amount']})")
        else:
            print(f"Response is not a dictionary with 'transactions' key: {type(response)}")
            if isinstance(response, dict):
                print(f"Response keys: {response.keys()}")
    
    except Exception as e:
        print(f"Error testing plaid.api.transactions.get: {str(e)}")
else:
    print("No Plaid items found in the database.") 