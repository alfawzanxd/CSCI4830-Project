from django.core.management.base import BaseCommand
from home.models import PlaidAccount

class Command(BaseCommand):
    help = 'Check account names in the database'

    def handle(self, *args, **options):
        accounts = PlaidAccount.objects.all()
        for account in accounts:
            self.stdout.write(f"Account ID: {account.account_id}")
            self.stdout.write(f"Account Name: {account.name}")
            self.stdout.write(f"Institution: {account.plaid_item.institution_name}")
            self.stdout.write("---") 