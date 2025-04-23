from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from home.models import PlaidItem, PlaidAccount
import plaid
from plaid.api import plaid_api
from django.conf import settings
from datetime import datetime

class Command(BaseCommand):
    help = 'Populates PlaidAccount model with account data from Plaid'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate PlaidAccount model...')
        
        # Initialize Plaid client
        configuration = plaid.Configuration(
            host='https://sandbox.plaid.com',
            api_key={
                'clientId': settings.PLAID_CLIENT_ID,
                'secret': settings.PLAID_SECRET,
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        plaid_client = plaid_api.PlaidApi(api_client)
        
        # Get all users with Plaid items
        users = User.objects.filter(plaiditem__isnull=False).distinct()
        
        for user in users:
            self.stdout.write(f'Processing user: {user.username}')
            
            # Get all Plaid items for this user
            plaid_items = PlaidItem.objects.filter(user=user)
            
            for item in plaid_items:
                self.stdout.write(f'Processing Plaid item: {item.item_id}')
                
                try:
                    # Get accounts from Plaid
                    accounts_request = plaid.model.accounts_get_request.AccountsGetRequest(
                        access_token=item.access_token
                    )
                    accounts_response = plaid_client.accounts_get(accounts_request)
                    
                    if hasattr(accounts_response, 'accounts'):
                        accounts = accounts_response.accounts
                        self.stdout.write(f'Found {len(accounts)} accounts for item {item.item_id}')
                        
                        for account in accounts:
                            # Update or create PlaidAccount
                            PlaidAccount.objects.update_or_create(
                                plaid_item=item,
                                account_id=account.account_id,
                                defaults={
                                    'name': account.name,
                                    'account_type': str(account.type),
                                    'account_subtype': str(account.subtype) if account.subtype else None,
                                    'mask': account.mask,
                                    'balance': account.balances.current if account.balances else 0.0
                                }
                            )
                            
                            self.stdout.write(f'Updated account: {account.name}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing item {item.item_id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully populated PlaidAccount model')) 