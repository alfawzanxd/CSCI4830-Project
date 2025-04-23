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