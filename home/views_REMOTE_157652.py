from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.conf import settings
import plaid
from plaid.api import plaid_api
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
import json
from .models import PlaidItem, PlaidTransaction, DailyTransactionSummary, PlaidAccount
from datetime import datetime, timedelta, date
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView, LoginView
from django.urls import reverse_lazy
from django.middleware.csrf import get_token
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from plaid.model.item import Item
import os

class AccountPageView(LoginRequiredMixin, View):
    login_url = 'login'  

    def get(self, request):
        return render(request, 'account.html')

@login_required(login_url='login')
def search_page(request):
    return render(request, 'search.html')

@login_required(login_url='login')
def account_page(request_obj):
    print(f"Account page accessed by user: {request_obj.user.username}")
    
    institutions = []
    has_linked_accounts = False
    
    try:
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request_obj.user)
        print(f"Found {len(plaid_items)} Plaid items for user")
        
        # Group accounts by institution
        for item in plaid_items:
            institution_accounts = PlaidAccount.objects.filter(plaid_item=item)
            if institution_accounts.exists():
                accounts = []
                for account in institution_accounts:
                    accounts.append({
                        'name': account.name,
                        'type': account.account_type,
                        'subtype': account.account_subtype,
                        'mask': account.mask,
                        'balance': float(account.balance)
                    })
                
                institutions.append({
                    'name': item.institution_name or 'Unknown Institution',
                    'item_id': item.item_id,
                    'accounts': accounts
                })
                print(f"Added institution: {item.institution_name} with item_id: {item.item_id}")
        
        has_linked_accounts = len(institutions) > 0
                
    except Exception as e:
        print(f"Error in account_page: {str(e)}")
        return render(request_obj, 'account.html', {
            'error': str(e),
            'institutions': [],
            'has_linked_accounts': False
        })
    
    print(f"Total institutions found: {len(institutions)}")
    return render(request_obj, 'account.html', {
        'institutions': institutions,
        'has_linked_accounts': has_linked_accounts
    })

@login_required(login_url='login')
def expense_page(request):
    return render(request, 'expense.html')

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

@login_required
def create_link_token(request):
    try:
        # Create a link token for the user
        link_token_request = {
            'user': {'client_user_id': str(request.user.id)},
            'client_name': 'OverseenBudget',
            'products': ['transactions'],
            'country_codes': ['US'],
            'language': 'en'
        }
        response = plaid_client.link_token_create(link_token_request)
        return JsonResponse(response.to_dict())
    except plaid.ApiException as e:
        print(f"Plaid API error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def test_link_token(request):
    try:
        # Create a test link token
        link_token_api = plaid.api.link_token.LinkToken(plaid_client)
        response = link_token_api.create({
            'user': {'client_user_id': str(request.user.id)},
            'client_name': 'OverseenBudget',
            'products': ['transactions'],
            'country_codes': ['US'],
            'language': 'en'
        })
        
        return JsonResponse(response)
    except plaid.errors.PlaidError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def exchange_public_token(request):
    try:
        data = json.loads(request.body)
        public_token = data.get('public_token')
        metadata = data.get('metadata', {})
        
        print(f"Exchange public token request - User: {request.user.username}")
        print(f"Metadata: {metadata}")
        
        if not public_token:
            return JsonResponse({'error': 'public_token must be a non-empty string'}, status=400)
        
        # Exchange public token
        exchange_request = plaid.model.item_public_token_exchange_request.ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        
        access_token = exchange_response.access_token
        item_id = exchange_response.item_id
        
        print(f"Exchange response - Item ID: {item_id}")
        
        # Get institution details from metadata
        institution = metadata.get('institution', {})
        institution_id = institution.get('institution_id')
        institution_name = institution.get('name')
        
        # If institution name is not in metadata, try to get it from the item
        if not institution_name:
            try:
                item_request = plaid.model.item_get_request.ItemGetRequest(
                    access_token=access_token
                )
                item_response = plaid_client.item_get(item_request)
                if hasattr(item_response, 'item'):
                    # Get the institution name from the item
                    institution_name = item_response.item.institution_name
                    if not institution_name:
                        # If still no name, try to get it from the institution ID
                        institution_name = item_response.item.institution_id
            except Exception as e:
                print(f"Error getting institution name from item: {str(e)}")
        
        # Remove 'Plaid' prefix if present
        if institution_name and institution_name.startswith('Plaid '):
            institution_name = institution_name[6:]  # Remove 'Plaid ' prefix
        
        print(f"Institution ID: {institution_id}, Name: {institution_name}")
        
        # Check if this item already exists
        existing_item = PlaidItem.objects.filter(
            user=request.user,
            item_id=item_id
        ).first()
        
        if existing_item:
            existing_item.access_token = access_token
            existing_item.institution_id = institution_id
            existing_item.institution_name = institution_name
            existing_item.save()
            print(f"Updated existing PlaidItem: {existing_item.id}")
            accounts_request = plaid.model.accounts_get_request.AccountsGetRequest(
                access_token=access_token
            )
            accounts_response = plaid_client.accounts_get(accounts_request)

            if hasattr(accounts_response, 'accounts'):
                for account in accounts_response.accounts:
                    PlaidAccount.objects.update_or_create(
                        plaid_item=existing_item,
                        account_id=account.account_id,
                        defaults={
                            'name': account.name,
                            'account_type': account.type,
                            'account_subtype': account.subtype,
                            'mask': account.mask,
                            'balance': account.balances.current
                        }
                    )
            return JsonResponse({'status': 'success', 'message': 'Account updated successfully'})
        
        # Create new item
        plaid_item = PlaidItem.objects.create(
            user=request.user,
            access_token=access_token,
            item_id=item_id,
            institution_id=institution_id,
            institution_name=institution_name
        )
        
        print(f"Created new PlaidItem: {plaid_item.id}")
        accounts_request = plaid.model.accounts_get_request.AccountsGetRequest(
            access_token=access_token
        )
        accounts_response = plaid_client.accounts_get(accounts_request)

        if hasattr(accounts_response, 'accounts'):
            for account in accounts_response.accounts:
                PlaidAccount.objects.create(
                    plaid_item=plaid_item,
                    account_id=account.account_id,
                    name=account.name,
                    account_type=account.type,
                    account_subtype=account.subtype,
                    mask=account.mask,
                    balance=account.balances.current
                )

        return JsonResponse({'status': 'success', 'message': 'Account added successfully'})
        
    except plaid.ApiException as e:
        print(f"Plaid API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def sync_transactions(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    try:
        print("Starting transaction sync...")
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {plaid_items.count()} Plaid items for user {request.user.username}")
        for item in plaid_items:
            print(f"Processing item: {item.item_id}")
            # Get transactions using the plaid client
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            print(f"Fetching transactions from {start_date} to {end_date}")
            transactions_request = plaid.model.transactions_get_request.TransactionsGetRequest(
                access_token=item.access_token,
                start_date=start_date,
                end_date=end_date
            )
            
            response = plaid_client.transactions_get(transactions_request)
            
            if hasattr(response, 'transactions'):
                transactions = response.transactions
                print(f"Found {len(transactions)} transactions from Plaid")
                for transaction in transactions:
                    # Check if transaction already exists
                    existing_transaction = PlaidTransaction.objects.filter(
                        transaction_id=transaction.transaction_id
                    ).first()
                    
                    if existing_transaction:
                        # Update existing transaction if needed
                        existing_transaction.amount = transaction.amount
                        existing_transaction.merchant_name = transaction.merchant_name or transaction.name
                        existing_transaction.description = transaction.name
                        existing_transaction.category = ','.join(transaction.category or [])
                        existing_transaction.save()
                        print(f"Updated transaction: {transaction.transaction_id}")
                    else:
                        # Create new transaction
                        PlaidTransaction.objects.create(
                            plaid_item=item,
                            transaction_id=transaction.transaction_id,
                            account_id=transaction.account_id,
                            amount=transaction.amount,
                            date=transaction.date,
                            merchant_name=transaction.merchant_name or transaction.name,
                            description=transaction.name,
                            category=','.join(transaction.category or [])
                        )
                        print(f"Created new transaction: {transaction.transaction_id}")
        
        # Update daily transaction summaries after syncing transactions
        update_daily_transaction_summaries(request.user)
        print("Transaction sync completed successfully")
        return JsonResponse({'status': 'success', 'message': 'Transactions synced successfully'})
    except plaid.ApiException as e:
        print(f"Plaid API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def update_daily_transaction_summaries(user):
    """
    Update the daily transaction summaries for a user based on their transactions.
    This function should be called after syncing transactions from Plaid.
    """
    try:
        # Get all transactions for the user
        plaid_items = PlaidItem.objects.filter(user=user)
        transactions = PlaidTransaction.objects.filter(plaid_item__in=plaid_items)
        
        # Group transactions by date
        transactions_by_date = {}
        for transaction in transactions:
            date_str = transaction.date.strftime('%Y-%m-%d')
            if date_str not in transactions_by_date:
                transactions_by_date[date_str] = []
            transactions_by_date[date_str].append(transaction)
        
        # Update or create daily summaries
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
        
        print(f"Updated daily transaction summaries for {len(transactions_by_date)} days")
        return True
    except Exception as e:
        print(f"Error updating daily transaction summaries: {str(e)}")
        return False

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('account')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')
    
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')

@csrf_exempt
def debug_plaid(request):
    try:
        # Print all available methods on the Plaid client
        print("Plaid client methods:")
        for method in dir(plaid_client):
            if not method.startswith('_'):
                print(f"- {method}")
        
        # Print all available methods on plaid.api
        print("\nPlaid API methods:")
        for module in dir(plaid.api):
            if not module.startswith('_'):
                print(f"- {module}")
        
        # Try to create a link token using different methods
        print("\nTrying different methods to create a link token:")
        
        # Method 1: Using plaid_client directly
        try:
            print("Method 1: plaid_client.link_token_create")
            response = plaid_client.link_token_create({
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
            link_token_api = plaid.api.link_token.LinkToken(plaid_client)
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
        
        return JsonResponse({'status': 'Debug information printed to console'})
    except Exception as e:
        print(f"Unexpected error in debug_plaid: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'login.html'
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        return super().form_valid(form)

@csrf_exempt
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('account')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('account')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    else:
        return render(request, 'login.html')

@login_required
def get_transactions(request):
    try:
        # Get filter parameters
        account_id = request.GET.get('account_id')
        institution = request.GET.get('institution')
        account_type = request.GET.get('account_type')
        
        print(f"Getting transactions with filters: account_id={account_id}, institution={institution}, account_type={account_type}")
        
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {len(plaid_items)} Plaid items for user {request.user.username}")
        
        # Track accounts with transactions
        accounts_with_transactions = set()
        
        # Get transactions for each item
        all_transactions = []
        seen_transactions = set()  # For deduplication
        
        for item in plaid_items:
            try:
                # Get transactions for this item
                # Get transactions from the last 30 days
                end_date = date.today()
                start_date = end_date - timedelta(days=30)
                
                transactions_request = plaid.model.transactions_get_request.TransactionsGetRequest(
                    access_token=item.access_token,
                    start_date=start_date,
                    end_date=end_date
                )
                
                response = plaid_client.transactions_get(transactions_request)
                
                # Process transactions
                for transaction in response.transactions:
                    # Create unique key for deduplication
                    unique_key = f"{transaction.date}_{transaction.amount}_{transaction.merchant_name}_{transaction.account_id}"
                    
                    if unique_key in seen_transactions:
                        continue
                    seen_transactions.add(unique_key)
                    
                    # Track which accounts have transactions
                    accounts_with_transactions.add(transaction.account_id)
                    
                    # Get account details
                    try:
                        account = PlaidAccount.objects.get(account_id=transaction.account_id)
                        account_name = account.name
                        institution_name = account.plaid_item.institution_name
                        
                        # Remove 'Plaid' prefix if present
                        if institution_name and institution_name.startswith('Plaid '):
                            institution_name = institution_name[6:]  # Remove 'Plaid ' prefix
                    except PlaidAccount.DoesNotExist:
                        account_name = "Unknown Account"
                        institution_name = "Unknown Institution"
                    
                    # Apply filters
                    if account_id and transaction.account_id != account_id:
                        continue
                    if institution and institution_name != institution:
                        continue
                    
                    PlaidTransaction.objects.update_or_create(
                        plaid_item=item,
                        transaction_id=transaction.transaction_id,
                        defaults={
                            'account_id': transaction.account_id,
                            'amount': transaction.amount,
                            'date': transaction.date,
                            'merchant_name': transaction.merchant_name or transaction.name,
                            'description': transaction.name,
                            'category': ','.join(transaction.category or [])
                        }
                    )

                    transaction_data = {
                        'date': transaction.date,
                        'merchant_name': transaction.merchant_name or transaction.name,
                        'amount': transaction.amount,
                        'category': transaction.category[0] if transaction.category else 'Uncategorized',
                        'account_name': account_name,
                        'institution': institution_name,
                        'account_id': transaction.account_id
                    }
                    
                    all_transactions.append(transaction_data)
                
            except Exception as e:
                print(f"Error getting transactions for item: {e}")
                continue
        
        # Update has_transactions flag for all accounts
        PlaidAccount.objects.filter(plaid_item__user=request.user).update(has_transactions=False)
        PlaidAccount.objects.filter(
            plaid_item__user=request.user,
            account_id__in=accounts_with_transactions
        ).update(has_transactions=True)
        
        # Sort transactions by date (newest first)
        all_transactions.sort(key=lambda x: x['date'], reverse=True)
        
        print(f"Found {len(all_transactions)} transactions")
        return JsonResponse({'transactions': all_transactions})
        
    except Exception as e:
        print(f"Error in get_transactions: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')
def search_transactions(request):
    print("Search transactions view called")
    date_str = request.GET.get('date')
    print(f"Search date: {date_str}")
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter is required'}, status=400)
    
    try:
        search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        print(f"Parsed date: {search_date}")
    except ValueError:
        print("Invalid date format")
        return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD'}, status=400)
    
    try:
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {plaid_items.count()} Plaid items")
        
        # Get transactions for the specified date
        transactions = PlaidTransaction.objects.filter(
            plaid_item__in=plaid_items,
            date=search_date
        ).select_related('plaid_item')
        
        print(f"Found {transactions.count()} transactions for date {search_date}")
        
        # Create a set to track unique transactions
        seen_transactions = set()
        unique_transactions = []
        
        for transaction in transactions:
            # Create a unique identifier for the transaction
            transaction_id = (
                transaction.date,
                transaction.merchant_name,
                transaction.amount,
                transaction.category
            )
            
            if transaction_id not in seen_transactions:
                seen_transactions.add(transaction_id)
                
                # Get account details
                try:
                    account = PlaidAccount.objects.get(account_id=transaction.account_id)
                    account_name = account.name
                except PlaidAccount.DoesNotExist:
                    account_name = "Unknown Account"
                
                # Determine if it's a credit or debit transaction
                is_credit = transaction.amount > 0
                
                # Use absolute value for amount
                abs_amount = abs(transaction.amount)
                
                unique_transactions.append({
                    'date': transaction.date.strftime('%Y-%m-%d'),
                    'merchant_name': transaction.merchant_name,
                    'amount': str(abs_amount),
                    'type': 'credit' if is_credit else 'debit',
                    'category': transaction.category,
                    'account_name': account_name
                })
        
        # Update daily transaction summaries for this date
        update_daily_transaction_summaries(request.user)
        
        print(f"Returning {len(unique_transactions)} unique transactions")
        return JsonResponse({'transactions': unique_transactions})
        
    except Exception as e:
        print(f"Error in search_transactions: {str(e)}")
        return JsonResponse({'error': 'An error occurred while searching transactions'}, status=500)

@login_required(login_url='login')
def get_calendar_transactions(request):
    try:
        # Get the current month and year from the request, or use current date
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        
        # Calculate the first and last day of the month
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        print(f"Fetching transaction summaries for {first_day} to {last_day}")
        
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {plaid_items.count()} Plaid items")
        
        # Get transactions for the specified date range
        transactions = PlaidTransaction.objects.filter(
            plaid_item__in=plaid_items,
            date__gte=first_day,
            date__lte=last_day
        ).select_related('plaid_item')
        
        print(f"Found {transactions.count()} transactions for the month")
        
        # Group transactions by date
        transactions_by_date = {}
        
        # First, initialize all dates in the month with empty transaction lists
        current_date = first_day
        while current_date <= last_day:
            date_str = current_date.strftime('%Y-%m-%d')
            transactions_by_date[date_str] = []
            current_date += timedelta(days=1)
        
        # Then, populate with actual transaction data
        for transaction in transactions:
            date_str = transaction.date.strftime('%Y-%m-%d')
            
            # Get the institution name, ensuring it's not None or empty
            institution_name = transaction.plaid_item.institution_name
            if not institution_name:
                institution_name = "Plaid Institution"
            
            # Determine if it's a credit or debit based on the amount and category
            amount = transaction.amount
            category = transaction.category or ''
            merchant_name = transaction.merchant_name or transaction.description or 'Unknown'
            
            # First check for income categories (Transfers, Deposits, Payroll)
            if ('Transfer' in category or 
                'Deposit' in category or 
                'Payroll' in category or
                'payroll' in merchant_name.lower() or
                'direct deposit' in merchant_name.lower()):
                # For these categories, positive amount = money in (credit)
                is_credit = amount > 0
            # Then check for expense categories (Travel, Transportation)
            elif ('Travel' in category or 
                  'Transportation' in category or
                  'airline' in merchant_name.lower() or
                  'hotel' in merchant_name.lower() or
                  'uber' in merchant_name.lower() or
                  'lyft' in merchant_name.lower()):
                # Travel services are always expenses (money out)
                is_credit = False
            # For all other transactions
            else:
                # For regular transactions, positive amount means expense (money out)
                is_credit = amount < 0
            
            # Create a transaction entry with the correct sign
            transaction_entry = {
                'merchant_name': merchant_name,
                'amount': str(abs(amount)),  # Store absolute value
                'type': 'credit' if is_credit else 'debit',
                'category': category or 'Uncategorized',
                'account_type': 'Summary',
                'institution': institution_name,
                'signed_amount': str(abs(amount) if is_credit else -abs(amount))  # Store signed amount for calendar
            }
            
            transactions_by_date[date_str].append(transaction_entry)
        
        # Debug: Print the first few date keys to verify format
        date_keys = list(transactions_by_date.keys())
        if date_keys:
            print(f"Sample date keys: {date_keys[:3]}")
            print(f"Sample transactions for first date: {transactions_by_date[date_keys[0]]}")
        
        return JsonResponse({'transactions': transactions_by_date})
        
    except Exception as e:
        print(f"Error in get_calendar_transactions: {str(e)}")
        return JsonResponse({'error': 'An error occurred while fetching calendar transactions'}, status=500)

@login_required
def get_accounts(request):
    try:
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {len(plaid_items)} Plaid items for user {request.user.username}")
        
        accounts_list = []
        seen_accounts = set()
        
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
        
        for item in plaid_items:
            try:
                # Get accounts for this item
                accounts_request = plaid.model.accounts_get_request.AccountsGetRequest(
                    access_token=item.access_token
                )
                response = plaid_client.accounts_get(accounts_request)
                
                # Process each account
                for account in response.accounts:
                    account_id = account.account_id
                    
                    # Skip if we've seen this account
                    if account_id in seen_accounts:
                        continue
                    seen_accounts.add(account_id)
                    
                    # Get account name and remove 'Plaid' prefix if present
                    account_name = account.name
                    if account_name and account_name.startswith('Plaid '):
                        account_name = account_name[6:]  # Remove 'Plaid ' prefix
                    
                    # Create or update account in database
                    plaid_account, created = PlaidAccount.objects.update_or_create(
                        plaid_item=item,
                        account_id=account_id,
                        defaults={
                            'name': account_name,
                            'account_type': str(account.type),
                            'account_subtype': str(account.subtype) if account.subtype else None,
                            'mask': account.mask,
                            'balance': account.balances.current if account.balances else 0
                        }
                    )
                    
                    # Get institution name and remove 'Plaid' prefix if present
                    institution_name = item.institution_name
                    if institution_name and institution_name.startswith('Plaid '):
                        institution_name = institution_name[6:]  # Remove 'Plaid ' prefix
                    
                    # Add to response list
                    accounts_list.append({
                        'account_id': account_id,
                        'name': account_name,
                        'type': str(account.type),
                        'subtype': str(account.subtype) if account.subtype else None,
                        'institution': institution_name,
                        'has_transactions': plaid_account.has_transactions
                    })
            
            except Exception as e:
                print(f"Error getting accounts for item: {e}")
                continue
        
        print(f"Found {len(accounts_list)} unique accounts")
        return JsonResponse({'accounts': accounts_list})
        
    except Exception as e:
        print(f"Error in get_accounts: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
def unlink_account(request):
    try:
        print("Unlink account request received")
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        print(f"Attempting to unlink account with item_id: {item_id}")
        
        if not item_id:
            print("Error: No item_id provided")
            return JsonResponse({'error': 'item_id is required'}, status=400)
            
        # Find the Plaid item
        plaid_item = PlaidItem.objects.filter(
            user=request.user,
            item_id=item_id
        ).first()
        
        if not plaid_item:
            print(f"Error: No PlaidItem found with item_id {item_id}")
            return JsonResponse({'error': 'Account not found'}, status=404)
            
        print(f"Found PlaidItem: {plaid_item.id}")
        
        # Delete the item from Plaid
        try:
            print("Attempting to remove item from Plaid")
            remove_request = plaid.model.item_remove_request.ItemRemoveRequest(
                access_token=plaid_item.access_token
            )
            plaid_client.item_remove(remove_request)
            print("Successfully removed item from Plaid")
        except plaid.ApiException as e:
            print(f"Error removing item from Plaid: {str(e)}")
            # Continue with deletion even if Plaid removal fails
            
        # Delete the item from our database
        print("Deleting PlaidItem from database")
        plaid_item.delete()
        print("Successfully deleted PlaidItem from database")
        
        return JsonResponse({'status': 'success', 'message': 'Account unlinked successfully'})
        
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Unexpected error in unlink_account: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

