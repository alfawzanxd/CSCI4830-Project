from django.db import models
from django.contrib.auth.models import User

class PlaidItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=200)
    item_id = models.CharField(max_length=200)
    institution_id = models.CharField(max_length=200, null=True, blank=True)
    institution_name = models.CharField(max_length=200, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'item_id')

    def __str__(self):
        return f"{self.institution_name} - {self.item_id}"

class PlaidAccount(models.Model):
    plaid_item = models.ForeignKey(PlaidItem, on_delete=models.CASCADE, related_name='accounts')
    account_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=50)
    account_subtype = models.CharField(max_length=50, null=True, blank=True)
    mask = models.CharField(max_length=10, null=True, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    has_transactions = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('plaid_item', 'account_id')
        indexes = [
            models.Index(fields=['plaid_item', 'account_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.plaid_item.institution_name})"

    @property
    def institution_name(self):
        return self.plaid_item.institution_name if self.plaid_item else "Unknown Institution"

    @property
    def user(self):
        return self.plaid_item.user if self.plaid_item else None

class PlaidTransaction(models.Model):
    plaid_item = models.ForeignKey(PlaidItem, on_delete=models.CASCADE, related_name='transactions')
    account_id = models.CharField(max_length=200)
    transaction_id = models.CharField(max_length=200)
    category = models.CharField(max_length=200, null=True, blank=True)
    date = models.DateField()
    merchant_name = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    pending = models.BooleanField(default=False)

    class Meta:
        unique_together = ('plaid_item', 'transaction_id')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['plaid_item', 'account_id']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.date} - {self.merchant_name or self.description} (${self.amount})"

class DailyTransactionSummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.date} - {self.user.username} (${self.total_amount})"

# Create your models here.
