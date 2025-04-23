import plaid
import django
import os
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'overseenbudget.settings')
django.setup()

from django.conf import settings

# Print Plaid version
print(f"Plaid version: {plaid.__version__}")

# Initialize Plaid client
client = plaid.Client(
    client_id=settings.PLAID_CLIENT_ID,
    secret=settings.PLAID_SECRET,
    environment=settings.PLAID_ENV
)

# Print all available methods on plaid.api.item
print("\nAvailable methods on plaid.api.item:")
for method in dir(plaid.api.item):
    if not method.startswith('_'):
        print(f"- {method}")

# Print all available methods on plaid.api.item.Item
print("\nAvailable methods on plaid.api.item.Item:")
item_api = plaid.api.item.Item(client)
for method in dir(item_api):
    if not method.startswith('_'):
        print(f"- {method}")

# Try different methods for exchanging public token
print("\nTrying different methods for exchanging public token:")

# Method 1: Using plaid.api.item.Item
try:
    print("\nMethod 1: plaid.api.item.Item")
    item_api = plaid.api.item.Item(client)
    print("Available methods:", [m for m in dir(item_api) if not m.startswith('_')])
except Exception as e:
    print(f"Error: {str(e)}")

# Method 2: Using plaid.api.item.PublicToken
try:
    print("\nMethod 2: plaid.api.item.PublicToken")
    public_token_api = plaid.api.item.PublicToken(client)
    print("Available methods:", [m for m in dir(public_token_api) if not m.startswith('_')])
except Exception as e:
    print(f"Error: {str(e)}") 