import plaid
import django
import os
import sys
import inspect

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'overseenbudget.settings')
django.setup()

from django.conf import settings
from home.models import PlaidItem

# Print Plaid version
print(f"Plaid version: {plaid.__version__}")

# Initialize Plaid client
client = plaid.Client(
    client_id=settings.PLAID_CLIENT_ID,
    secret=settings.PLAID_SECRET,
    environment=settings.PLAID_ENV
)

# Print all available methods on the client
print("\nAvailable methods on plaid.Client:")
for method in dir(client):
    if not method.startswith('_'):
        print(f"- {method}")

# Print all available methods on plaid.api
print("\nAvailable methods on plaid.api:")
for module in dir(plaid.api):
    if not module.startswith('_'):
        print(f"- {module}")

# Check specific API modules
print("\nChecking specific API modules:")

# Check Accounts API
accounts_api = client.Accounts
print("\nAccounts API:")
print(f"Type: {type(accounts_api)}")
print("Methods:")
for method in dir(accounts_api):
    if not method.startswith('_'):
        print(f"- {method}")

# Check Transactions API
transactions_api = client.Transactions
print("\nTransactions API:")
print(f"Type: {type(transactions_api)}")
print("Methods:")
for method in dir(transactions_api):
    if not method.startswith('_'):
        print(f"- {method}")

# Check Item API
item_api = client.Item
print("\nItem API:")
print(f"Type: {type(item_api)}")
print("Methods:")
for method in dir(item_api):
    if not method.startswith('_'):
        print(f"- {method}")

# Check LinkToken API
link_token_api = client.LinkToken
print("\nLinkToken API:")
print(f"Type: {type(link_token_api)}")
print("Methods:")
for method in dir(link_token_api):
    if not method.startswith('_'):
        print(f"- {method}")

# Get the first Plaid item
plaid_items = PlaidItem.objects.all()
if plaid_items.exists():
    item = plaid_items.first()
    print(f"\nTesting with Plaid Item ID: {item.id}")
    print(f"Access Token: {item.access_token[:10]}...")
    
    # Try to create an Accounts instance
    try:
        print("\nTrying to create an Accounts instance:")
        accounts_api = client.Accounts(access_token=item.access_token)
        print(f"Accounts API type: {type(accounts_api)}")
        print("Methods:")
        for method in dir(accounts_api):
            if not method.startswith('_'):
                print(f"- {method}")
    except Exception as e:
        print(f"Error creating Accounts instance: {str(e)}")
    
    # Try to create a Transactions instance
    try:
        print("\nTrying to create a Transactions instance:")
        transactions_api = client.Transactions(access_token=item.access_token)
        print(f"Transactions API type: {type(transactions_api)}")
        print("Methods:")
        for method in dir(transactions_api):
            if not method.startswith('_'):
                print(f"- {method}")
    except Exception as e:
        print(f"Error creating Transactions instance: {str(e)}")
else:
    print("No Plaid items found in the database.")

# Try to create a link token using different methods
print("\nTrying different methods to create a link token:")

# Method 1: Using client directly
try:
    print("\nMethod 1: client.link_token_create")
    response = client.link_token_create({
        'user': {'client_user_id': 'test'},
        'client_name': 'Test',
        'products': ['transactions'],
        'country_codes': ['US'],
        'language': 'en'
    })
    print("Success!")
except Exception as e:
    print(f"Error: {str(e)}")

# Method 2: Using plaid.api.link_token.create
try:
    print("\nMethod 2: plaid.api.link_token.create")
    response = plaid.api.link_token.create({
        'user': {'client_user_id': 'test'},
        'client_name': 'Test',
        'products': ['transactions'],
        'country_codes': ['US'],
        'language': 'en'
    })
    print("Success!")
except Exception as e:
    print(f"Error: {str(e)}")

# Method 3: Using plaid.api.link_token.LinkToken
try:
    print("\nMethod 3: plaid.api.link_token.LinkToken")
    link_token_api = plaid.api.link_token.LinkToken(client)
    response = link_token_api.create({
        'user': {'client_user_id': 'test'},
        'client_name': 'Test',
        'products': ['transactions'],
        'country_codes': ['US'],
        'language': 'en'
    })
    print("Success!")
except Exception as e:
    print(f"Error: {str(e)}")

# Check if specific methods exist
print("\nChecking for specific methods:")
methods_to_check = [
    'accounts_get',
    'transactions_get',
    'create_link_token',
    'link_token_create',
    'exchange_public_token',
    'item_public_token_exchange',
    'item_get',
    'accounts',
    'transactions'
]

for method in methods_to_check:
    exists = hasattr(client, method)
    print(f"- {method}: {'Exists' if exists else 'Does not exist'}")

# Check if specific API modules exist
api_modules_to_check = [
    'accounts',
    'transactions',
    'link_token',
    'item'
]

for module in api_modules_to_check:
    exists = hasattr(plaid.api, module)
    print(f"- plaid.api.{module}: {'Exists' if exists else 'Does not exist'}") 