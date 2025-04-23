import os
import django
import plaid
import inspect

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

# Print Plaid version
print(f"Plaid version: {plaid.__version__}")

# Print all available methods on the Plaid client
print("\nAvailable methods on plaid_client:")
for method in dir(plaid_client):
    if not method.startswith('_'):
        print(f"- {method}")

# Print all available methods on plaid.api
print("\nAvailable methods on plaid.api:")
for module in dir(plaid.api):
    if not module.startswith('_'):
        print(f"- {module}")

# Check specific API modules
print("\nChecking specific API modules:")

# Check accounts API
if hasattr(plaid.api, 'accounts'):
    print("\nAccounts API:")
    accounts_api = plaid.api.accounts
    print(f"Type: {type(accounts_api)}")
    print("Methods:")
    for method in dir(accounts_api):
        if not method.startswith('_'):
            print(f"- {method}")
    
    # Check if there's a get method
    if hasattr(accounts_api, 'get'):
        print("\nAccounts API has a 'get' method")
        print(f"Method signature: {inspect.signature(accounts_api.get)}")
    else:
        print("\nAccounts API does not have a 'get' method")

# Check transactions API
if hasattr(plaid.api, 'transactions'):
    print("\nTransactions API:")
    transactions_api = plaid.api.transactions
    print(f"Type: {type(transactions_api)}")
    print("Methods:")
    for method in dir(transactions_api):
        if not method.startswith('_'):
            print(f"- {method}")
    
    # Check if there's a get method
    if hasattr(transactions_api, 'get'):
        print("\nTransactions API has a 'get' method")
        print(f"Method signature: {inspect.signature(transactions_api.get)}")
    else:
        print("\nTransactions API does not have a 'get' method")

# Check item API
if hasattr(plaid.api, 'item'):
    print("\nItem API:")
    item_api = plaid.api.item
    print(f"Type: {type(item_api)}")
    print("Methods:")
    for method in dir(item_api):
        if not method.startswith('_'):
            print(f"- {method}")
    
    # Check if there's a public_token_exchange method
    if hasattr(item_api, 'public_token_exchange'):
        print("\nItem API has a 'public_token_exchange' method")
        print(f"Method signature: {inspect.signature(item_api.public_token_exchange)}")
    else:
        print("\nItem API does not have a 'public_token_exchange' method")

# Check link_token API
if hasattr(plaid.api, 'link_token'):
    print("\nLink Token API:")
    link_token_api = plaid.api.link_token
    print(f"Type: {type(link_token_api)}")
    print("Methods:")
    for method in dir(link_token_api):
        if not method.startswith('_'):
            print(f"- {method}")
    
    # Check if there's a create method
    if hasattr(link_token_api, 'create'):
        print("\nLink Token API has a 'create' method")
        print(f"Method signature: {inspect.signature(link_token_api.create)}")
    else:
        print("\nLink Token API does not have a 'create' method") 