from django.core.management.base import BaseCommand
from home.models import PlaidItem

class Command(BaseCommand):
    help = 'Check institution names in the database'

    def handle(self, *args, **options):
        items = PlaidItem.objects.all()
        for item in items:
            self.stdout.write(f"Item ID: {item.item_id}")
            self.stdout.write(f"Institution Name: {item.institution_name}")
            self.stdout.write("---") 