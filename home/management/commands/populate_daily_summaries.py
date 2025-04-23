from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from home.models import PlaidTransaction, DailyTransactionSummary
from datetime import datetime
from django.db.models import Sum, Count

class Command(BaseCommand):
    help = 'Populates daily transaction summaries for all users'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate daily transaction summaries...')
        
        # Get all users with Plaid transactions
        users = User.objects.filter(plaiditem__transactions__isnull=False).distinct()
        
        for user in users:
            self.stdout.write(f'Processing user: {user.username}')
            
            # Get all transactions for this user
            plaid_items = user.plaiditem_set.all()
            transactions = PlaidTransaction.objects.filter(plaid_item__in=plaid_items)
            
            # Group transactions by date
            transactions_by_date = {}
            for transaction in transactions:
                date_str = transaction.date.strftime('%Y-%m-%d')
                if date_str not in transactions_by_date:
                    transactions_by_date[date_str] = []
                transactions_by_date[date_str].append(transaction)
            
            # Create or update daily summaries
            for date_str, date_transactions in transactions_by_date.items():
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Calculate total amount and transaction count
                total_amount = sum(t.amount for t in date_transactions)
                transaction_count = len(date_transactions)
                
                # Update or create the daily summary
                DailyTransactionSummary.objects.update_or_create(
                    user=user,
                    date=date_obj,
                    defaults={
                        'total_amount': total_amount,
                        'transaction_count': transaction_count
                    }
                )
            
            self.stdout.write(f'Created/updated {len(transactions_by_date)} daily summaries for user {user.username}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated daily transaction summaries')) 