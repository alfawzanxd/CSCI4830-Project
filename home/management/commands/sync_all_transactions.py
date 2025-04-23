from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from home.models import PlaidItem, PlaidTransaction
import plaid
from plaid.api import plaid_api
from django.conf import settings
from datetime import datetime, timedelta, date

class Command(BaseCommand):
    help = 'Syncs transactions for all Plaid items'

    def handle(self, *args, **options):
        self.stdout.write('Starting to sync transactions...')
        
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
                    # Get transactions from the last 30 days
                    end_date = date.today()
                    start_date = end_date - timedelta(days=30)
                    
                    transactions_request = plaid.model.transactions_get_request.TransactionsGetRequest(
                        access_token=item.access_token,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    response = plaid_client.transactions_get(transactions_request)
                    
                    if hasattr(response, 'transactions'):
                        transactions = response.transactions
                        self.stdout.write(f'Found {len(transactions)} transactions for item {item.item_id}')
                        
                        for transaction in transactions:
                            # Create or update transaction
                            PlaidTransaction.objects.update_or_create(
                                plaid_item=item,
                                transaction_id=transaction.transaction_id,
                                defaults={
                                    'account_id': transaction.account_id,
                                    'amount': transaction.amount,
                                    'date': transaction.date,
                                    'merchant_name': transaction.merchant_name or transaction.name,
                                    'description': transaction.name,
                                    'category': ','.join(transaction.category or []),
                                    'pending': transaction.pending
                                }
                            )
                            
                        self.stdout.write(f'Successfully synced transactions for item {item.item_id}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing item {item.item_id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully synced all transactions')) 