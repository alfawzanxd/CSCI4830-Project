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
from decimal import Decimal
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string

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

@login_required(login_url='login')
def budget_page(request):
    # Get the selected account from the request
    selected_account = request.GET.get('account')
    
    # Get all Plaid items for the current user
    plaid_items = PlaidItem.objects.filter(user=request.user)
    
    # Get all accounts for the current user
    accounts = PlaidAccount.objects.filter(plaid_item__in=plaid_items)
    
    # Calculate current balance - only for selected account if specified
    if selected_account:
        current_balance = Decimal('0')
        try:
            selected_account_obj = PlaidAccount.objects.get(account_id=selected_account)
            current_balance = Decimal(str(selected_account_obj.balance))
        except PlaidAccount.DoesNotExist:
            current_balance = Decimal('0')
    else:
        # If no account selected, sum all accounts
        current_balance = sum(Decimal(str(account.balance)) for account in accounts)
    
    # Initialize totals
    total_income = Decimal('0')
    total_expenses = Decimal('0')
    cut_back_expenses = Decimal('0')
    necessary_expenses = Decimal('0')
    
    # Define categories for cut-back and necessary expenses
    cut_back_categories = [
        'Food and Drink', 'Shopping', 'Shops', 'Entertainment', 'Recreation',
        'Travel', 'Healthcare', 'Personal Care', 'Miscellaneous', 
        'Restaurants', 'Fast Food', 'Coffee Shop', 'Bar', 'Clothing', 
        'Electronics', 'Hobbies', 'Gifts', 'Sports', 'Movies', 'Music', 
        'Games', 'Dining', 'Food', 'Drink', 'Store', 'Retail', 'Merchandise',
        'Amusement', 'Leisure', 'Vacation', 'Hotel', 'Air Travel',
        'Entertainment', 'Recreation', 'Fitness', 'Gym', 'Spa',
        'Beauty', 'Cosmetics', 'Apparel', 'Accessories',
        'Gadgets', 'Hobby', 'Craft', 'Gift', 'Present', 'Sport',
        'Movie', 'Theater', 'Concert', 'Game', 'Video Game'
    ]
    
    necessary_categories = [
        'Rent', 'Utilities', 'Insurance', 'Loan Payments',
        'Education', 'Professional Services', 'Medical',
        'Child Care', 'Transportation', 'Mortgage', 'Electric',
        'Water', 'Gas', 'Internet', 'Phone', 'Car Payment',
        'Student Loan', 'Medical', 'Dental', 'Vision', 'Childcare',
        'Public Transit', 'Parking', 'Tolls', 'Payment', 'Transfer',
        'Tax', 'Bank Fees', 'Service Charges'
    ]

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
    
    # Get transactions for each item
    all_transactions = []
    cut_back_transactions = []
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
                
                # Apply account filter if selected
                if selected_account and transaction.account_id != selected_account:
                    continue
                
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
                
                # Process transaction for totals
                # Determine if it's a credit (money in) or debit (money out)
                category = transaction.category[0] if transaction.category else ''
                merchant_name = (transaction.merchant_name or transaction.name or '').lower()
                amount = Decimal(str(transaction.amount))
                
                print(f"\nProcessing transaction:")
                print(f"Merchant: {merchant_name}")
                print(f"Category: {category}")
                print(f"Raw amount: ${amount}")
                
                # First check for income categories (Transfers, Deposits, Payroll)
                if ('transfer' in category.lower() or 
                    'deposit' in category.lower() or 
                    'payroll' in category.lower() or
                    'payroll' in merchant_name or
                    'direct deposit' in merchant_name):
                    # For these categories, positive amount = money in (credit)
                    is_credit = amount > 0
                # Then check for expense categories (Travel, Transportation)
                elif ('travel' in category.lower() or 
                      'transportation' in category.lower() or
                      'airline' in merchant_name or
                      'hotel' in merchant_name or
                      'uber' in merchant_name or
                      'lyft' in merchant_name):
                    # Travel services are always expenses (money out)
                    is_credit = False
                # For all other transactions
                else:
                    # For regular transactions, positive amount means expense (money out)
                    is_credit = amount < 0
                
                # Calculate the actual amount (positive for income, negative for expenses)
                actual_amount = abs(amount) if is_credit else -abs(amount)
                print(f"Processed amount: ${actual_amount} ({'credit' if is_credit else 'debit'})")
                
                if actual_amount < 0:  # Negative amount means expense
                    expense_amount = abs(actual_amount)
                    total_expenses += expense_amount
                    
                    # Check if it's a payment-related transaction first
                    is_payment = (
                        'payment' in merchant_name or
                        'transfer' in merchant_name or
                        category.lower() == 'payment' or
                        category.lower() == 'transfer'
                    )

                    if is_payment:
                        # Payment transactions are necessary expenses
                        necessary_expenses += expense_amount
                        print(f"Found payment/transfer: {merchant_name} - {category} - ${expense_amount}")
                    else:
                        # Check if it's a cut back expense
                        is_cut_back = False
                        for cut_back in cut_back_categories:
                            if (cut_back.lower() in category.lower() or 
                                cut_back.lower() in merchant_name or
                                category.lower() in cut_back.lower()):
                                is_cut_back = True
                                print(f"Found cut back expense: {merchant_name} - {category} - ${expense_amount}")
                                print(f"Matched category: {cut_back}")
                                break
                        
                        if is_cut_back:
                            cut_back_expenses += expense_amount
                            # Add to cut back transactions list
                            cut_back_transactions.append({
                                'date': transaction.date,
                                'merchant_name': transaction.merchant_name or transaction.name,
                                'category': category,
                                'amount': expense_amount
                            })
                        else:
                            # Check if it's a necessary expense
                            is_necessary = False
                            for necessary in necessary_categories:
                                if (necessary.lower() in category.lower() or 
                                    necessary.lower() in merchant_name or
                                    category.lower() in necessary.lower()):
                                    is_necessary = True
                                    print(f"Found necessary expense: {merchant_name} - {category} - ${expense_amount}")
                                    print(f"Matched category: {necessary}")
                                    break
                            
                            if is_necessary:
                                necessary_expenses += expense_amount
                else:
                    # Positive amount means income
                    total_income += actual_amount
                    print(f"Found income: {merchant_name} - ${actual_amount}")
            
        except Exception as e:
            print(f"Error getting transactions for item: {e}")
            continue
    
    # Sort transactions by date (newest first)
    all_transactions.sort(key=lambda x: x['date'], reverse=True)
    cut_back_transactions.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate available balance
    available_balance = current_balance - total_expenses
    
    # Calculate cut back percentage
    cut_back_percentage = (cut_back_expenses / total_expenses * Decimal('100')) if total_expenses > 0 else Decimal('0')
    
    # Calculate potential balance (current balance + cut back expenses)
    potential_balance = current_balance + cut_back_expenses
    
    # Debug output
    print(f"Total Expenses: ${total_expenses}")
    print(f"Cut Back Expenses: ${cut_back_expenses}")
    print(f"Necessary Expenses: ${necessary_expenses}")
    print(f"Number of transactions: {len(all_transactions)}")
    print(f"Number of cut back transactions: {len(cut_back_transactions)}")
    
    context = {
        'accounts': accounts,
        'selected_account': selected_account,
        'current_balance': current_balance,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'cut_back_expenses': cut_back_expenses,
        'necessary_expenses': necessary_expenses,
        'available_balance': available_balance,
        'cut_back_percentage': cut_back_percentage,
        'potential_balance': potential_balance,
        'transactions': all_transactions,
        'cut_back_transactions': cut_back_transactions
    }
    
    return render(request, 'budget.html', context)

# Initialize Plaid client
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
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
        return JsonResponse({'status': 'success', 'message': 'Account added successfully'})
        
    except plaid.ApiException as e:
        print(f"Plaid API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_transactions(request):
    try:
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {plaid_items.count()} Plaid items for user {request.user.username}")
        
        total_transactions = 0
        
        for item in plaid_items:
            print(f"\nSyncing transactions for item: {item.institution_name} (ID: {item.item_id})")
            print(f"Access token: {item.access_token[:10]}...")
            
            try:
                # Get transactions from the last 30 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                
                print(f"Fetching transactions from {start_date} to {end_date}")
                
                transactions_request = plaid.model.transactions_get_request.TransactionsGetRequest(
                    access_token=item.access_token,
                    start_date=start_date,
                    end_date=end_date,
                    options={
                        'include_personal_finance_category': True,
                        'count': 500
                    }
                )
                
                response = plaid_client.transactions_get(transactions_request)
                print(f"Raw Plaid response: {response}")
                
                if hasattr(response, 'transactions'):
                    transactions = response.transactions
                    print(f"Found {len(transactions)} transactions from Plaid API")
                    
                    # Clear existing transactions for this date range
                    PlaidTransaction.objects.filter(
                        plaid_item=item,
                        date__gte=start_date,
                        date__lte=end_date
                    ).delete()
                    
                    # Add new transactions
                    for transaction in transactions:
                        print(f"Processing transaction: {transaction.name} - ${transaction.amount} on {transaction.date}")
                        
                        # Create new transaction
                        new_transaction = PlaidTransaction.objects.create(
                            plaid_item=item,
                            transaction_id=transaction.transaction_id,
                            account_id=transaction.account_id,
                            category=transaction.category[0] if transaction.category else None,
                            date=transaction.date,
                            merchant_name=transaction.merchant_name or transaction.name,
                            amount=transaction.amount,
                            description=transaction.name,
                            pending=transaction.pending
                        )
                        print(f"Created transaction: {new_transaction.id}")
                        total_transactions += 1
                    
                    print(f"Successfully synced {len(transactions)} transactions for this item")
                else:
                    print("No transactions found in Plaid API response")
                
            except plaid.ApiException as e:
                print(f"Plaid API error for item {item.id}: {str(e)}")
                print(f"Error body: {e.body}")
                continue
            except Exception as e:
                print(f"Error processing item {item.id}: {str(e)}")
                continue
        
        # Update daily transaction summaries
        update_daily_transaction_summaries(request.user)
        
        print(f"Total transactions synced: {total_transactions}")
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully synced {total_transactions} transactions',
            'transaction_count': total_transactions
        })
                
    except Exception as e:
        print(f"Error in sync_transactions: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

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
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'register.html')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'register.html')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'register.html')
            
        # Create user with email
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )
        
        login(request, user)
        return redirect('account')
        
    return render(request, 'register.html')

class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')
    
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')

@login_required
def debug_plaid(request):
    try:
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {plaid_items.count()} Plaid items for user {request.user.username}")
        
        for item in plaid_items:
            print(f"\nChecking Plaid item: {item.institution_name}")
            print(f"Item ID: {item.item_id}")
            print(f"Access Token: {item.access_token[:10]}...")
            
            # Try to get item details from Plaid
            try:
                item_request = plaid.model.item_get_request.ItemGetRequest(
                    access_token=item.access_token
                )
                item_response = plaid_client.item_get(item_request)
                print(f"Item status: {item_response.item.status}")
                print(f"Webhook: {item_response.item.webhook}")
                
                # Try to get accounts
                accounts_request = plaid.model.accounts_get_request.AccountsGetRequest(
                    access_token=item.access_token
                )
                accounts_response = plaid_client.accounts_get(accounts_request)
                print(f"Found {len(accounts_response.accounts)} accounts")
                
                # Try to get transactions
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                transactions_request = plaid.model.transactions_get_request.TransactionsGetRequest(
                    access_token=item.access_token,
                    start_date=start_date,
                    end_date=end_date
                )
                transactions_response = plaid_client.transactions_get(transactions_request)
                print(f"Found {len(transactions_response.transactions)} transactions")
                
                # Print first few transactions
                for transaction in transactions_response.transactions[:5]:
                    print(f"\nTransaction: {transaction.merchant_name} - ${transaction.amount} on {transaction.date}")
                    print(f"Category: {transaction.category}")
                    print(f"Account ID: {transaction.account_id}")
                
            except plaid.ApiException as e:
                print(f"Plaid API error: {str(e)}")
                print(f"Error body: {e.body}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        return JsonResponse({'status': 'success', 'message': 'Debug information printed to console'})
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
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'login.html')
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
        
        # Check if the date is within the last 30 days
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        if search_date < thirty_days_ago or search_date > datetime.now().date():
            return JsonResponse({
                'error': 'Date must be within the last 30 days',
                'valid_range': {
                    'start': thirty_days_ago.strftime('%Y-%m-%d'),
                    'end': datetime.now().date().strftime('%Y-%m-%d')
                }
            }, status=400)
            
    except ValueError:
        print("Invalid date format")
        return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD'}, status=400)
    
    try:
        # First sync transactions to ensure we have the latest data
        print("Syncing transactions before search...")
        sync_response = sync_transactions(request)
        
        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=request.user)
        print(f"Found {plaid_items.count()} Plaid items")
        
        if not plaid_items.exists():
            return JsonResponse({
                'error': 'No linked bank accounts found. Please link a bank account first.'
            }, status=400)
        
        # Get transactions for the specified date
        transactions = PlaidTransaction.objects.filter(
            plaid_item__in=plaid_items,
            date=search_date
        ).select_related('plaid_item')
        
        print(f"Found {transactions.count()} transactions for date {search_date}")
        
        if not transactions.exists():
            # Try to get transactions directly from Plaid
            print("No transactions in database, trying to get from Plaid directly...")
            
            unique_transactions = []
            for item in plaid_items:
                try:
                    transactions_request = plaid.model.transactions_get_request.TransactionsGetRequest(
                        access_token=item.access_token,
                        start_date=search_date,
                        end_date=search_date,
                        options={
                            'include_personal_finance_category': True,
                            'count': 500
                        }
                    )
                    
                    response = plaid_client.transactions_get(transactions_request)
                    
                    if hasattr(response, 'transactions'):
                        for transaction in response.transactions:
                            print(f"Found transaction from Plaid: {transaction.name} - ${transaction.amount}")
                            
                            # Get account details
                            try:
                                account = PlaidAccount.objects.get(account_id=transaction.account_id)
                                account_name = account.name
                            except PlaidAccount.DoesNotExist:
                                account_name = "Unknown Account"
                            
                            # Determine if it's a credit or debit transaction
                            is_credit = transaction.amount > 0
                            
                            unique_transactions.append({
                                'date': transaction.date,
                                'merchant_name': transaction.merchant_name or transaction.name,
                                'amount': str(abs(transaction.amount)),
                                'type': 'credit' if is_credit else 'debit',
                                'category': transaction.category[0] if transaction.category else 'Uncategorized',
                                'account_name': account_name
                            })
                            
                except Exception as e:
                    print(f"Error getting transactions from Plaid for item {item.id}: {str(e)}")
                    continue
            
            if unique_transactions:
                print(f"Found {len(unique_transactions)} transactions directly from Plaid")
                return JsonResponse({'transactions': unique_transactions})
            else:
                print("No transactions found for this date")
                return JsonResponse({'transactions': []})
        
        # If we have transactions in the database, return those
        unique_transactions = []
        seen_transactions = set()
        
        for transaction in transactions:
            print(f"Processing transaction: {transaction.merchant_name} - ${transaction.amount}")
            
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
                    print(f"Found account: {account_name}")
                except PlaidAccount.DoesNotExist:
                    account_name = "Unknown Account"
                    print(f"No account found for ID: {transaction.account_id}")
                
                # Determine if it's a credit or debit transaction
                is_credit = transaction.amount > 0
                print(f"Transaction type: {'credit' if is_credit else 'debit'}")
                
                unique_transactions.append({
                    'date': transaction.date.strftime('%Y-%m-%d'),
                    'merchant_name': transaction.merchant_name,
                    'amount': str(abs(transaction.amount)),
                    'type': 'credit' if is_credit else 'debit',
                    'category': transaction.category,
                    'account_name': account_name
                })
        
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

def update_budget_summary(user, account_id=None):
    """Update the budget summary for a user and optionally a specific account."""
    try:
        # Get the selected account if specified
        selected_account = None
        if account_id:
            try:
                selected_account = PlaidAccount.objects.get(account_id=account_id)
            except PlaidAccount.DoesNotExist:
                pass

        # Get all Plaid items for the user
        plaid_items = PlaidItem.objects.filter(user=user)
        
        # Get all accounts for the user
        accounts = PlaidAccount.objects.filter(plaid_item__in=plaid_items)
        
        # Calculate current balance
        if selected_account:
            current_balance = Decimal(str(selected_account.balance))
        else:
            current_balance = sum(Decimal(str(account.balance)) for account in accounts)
        
        # Initialize totals
        total_income = Decimal('0')
        total_expenses = Decimal('0')
        cut_back_expenses = Decimal('0')
        necessary_expenses = Decimal('0')
        
        # Get transactions for each item
        all_transactions = []
        cut_back_transactions = []
        seen_transactions = set()
        
        for item in plaid_items:
            try:
                # Get transactions for this item
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
                    
                    # Apply account filter if selected
                    if selected_account and transaction.account_id != selected_account.account_id:
                        continue
                    
                    # Process transaction for totals
                    category = transaction.category[0] if transaction.category else ''
                    merchant_name = (transaction.merchant_name or transaction.name or '').lower()
                    amount = Decimal(str(transaction.amount))
                    
                    # First check for income categories
                    if ('transfer' in category.lower() or 
                        'deposit' in category.lower() or 
                        'payroll' in category.lower() or
                        'payroll' in merchant_name or
                        'direct deposit' in merchant_name):
                        is_credit = amount > 0
                    elif ('travel' in category.lower() or 
                          'transportation' in category.lower() or
                          'airline' in merchant_name or
                          'hotel' in merchant_name or
                          'uber' in merchant_name or
                          'lyft' in merchant_name):
                        is_credit = False
                    else:
                        is_credit = amount < 0
                    
                    actual_amount = abs(amount) if is_credit else -abs(amount)
                    
                    if actual_amount < 0:  # Negative amount means expense
                        expense_amount = abs(actual_amount)
                        total_expenses += expense_amount
                        
                        # Check if it's a payment-related transaction
                        is_payment = (
                            'payment' in merchant_name or
                            'transfer' in merchant_name or
                            category.lower() == 'payment' or
                            category.lower() == 'transfer'
                        )

                        if is_payment:
                            necessary_expenses += expense_amount
                        else:
                            # Check if it's a cut back expense
                            is_cut_back = False
                            for cut_back in cut_back_categories:
                                if (cut_back.lower() in category.lower() or 
                                    cut_back.lower() in merchant_name or
                                    category.lower() in cut_back.lower()):
                                    is_cut_back = True
                                    break
                            
                            if is_cut_back:
                                cut_back_expenses += expense_amount
                            else:
                                # Check if it's a necessary expense
                                is_necessary = False
                                for necessary in necessary_categories:
                                    if (necessary.lower() in category.lower() or 
                                        necessary.lower() in merchant_name or
                                        category.lower() in necessary.lower()):
                                        is_necessary = True
                                        break
                                
                                if is_necessary:
                                    necessary_expenses += expense_amount
                    else:
                        # Positive amount means income
                        total_income += actual_amount
            
            except Exception as e:
                print(f"Error getting transactions for item: {e}")
                continue
        
        # Calculate derived values
        available_balance = current_balance - total_expenses
        cut_back_percentage = (cut_back_expenses / total_expenses * Decimal('100')) if total_expenses > 0 else Decimal('0')
        potential_balance = current_balance + cut_back_expenses
        
        # Create or update budget summary
        BudgetSummary.objects.update_or_create(
            user=user,
            account=selected_account,
            defaults={
                'current_balance': current_balance,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'cut_back_expenses': cut_back_expenses,
                'necessary_expenses': necessary_expenses,
                'available_balance': available_balance,
                'cut_back_percentage': cut_back_percentage,
                'potential_balance': potential_balance
            }
        )
        
        return True
    except Exception as e:
        print(f"Error updating budget summary: {e}")
        return False

def password_reset(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        print(f"Password reset requested for username: {username}")
        
        try:
            user = User.objects.get(username=username)
            print(f"Found user: {user.username} with email: {user.email}")
            
            if not user.email:
                print("ERROR: User has no email address set!")
                messages.error(request, 'Your account has no email address set. Please contact support.')
                return render(request, 'password_reset.html')
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build password reset URL
            reset_url = request.build_absolute_uri(
                reverse_lazy('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            print(f"Reset URL: {reset_url}")
            
            # Send email
            subject = 'Password Reset Request'
            message = f'''
            Hello {user.username},
            
            You requested to reset your password. Please click the link below to set a new password:
            
            {reset_url}
            
            If you didn't request this, you can safely ignore this email.
            
            Best regards,
            OverseenBudget Team
            '''
            
            print(f"Attempting to send email to: {user.email}")
            print(f"Using sender email: overseenbudget@gmail.com")
            try:
                send_mail(
                    subject,
                    message,
                    'overseenbudget@gmail.com',  # From email - must match EMAIL_HOST_USER
                    [user.email],  # Send to the email associated with the account
                    fail_silently=False,
                )
                print("Email sent successfully!")
            except Exception as e:
                print(f"Error sending email: {str(e)}")
                print(f"Error type: {type(e)}")
                print(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
                messages.error(request, f'Failed to send reset email: {str(e)}')
                return render(request, 'password_reset.html')
            
            # Show the success page with the email
            return render(request, 'password_reset_sent.html', {'email': user.email})
            
        except User.DoesNotExist:
            print(f"No user found with username: {username}")
            messages.error(request, 'No account found with that username.')
            return render(request, 'password_reset.html')
    
    return render(request, 'password_reset.html')

def password_reset_confirm(request, uidb64, token):
    try:
        # Decode the user ID
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        
        # Verify the token
        if not default_token_generator.check_token(user, token):
            messages.error(request, 'Password reset link is invalid or has expired.')
            return redirect('login')
        
        if request.method == 'POST':
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            if new_password1 != new_password2:
                return render(request, 'password_reset_confirm.html', {
                    'error': 'Passwords do not match.'
                })
            
            if len(new_password1) < 8:
                return render(request, 'password_reset_confirm.html', {
                    'error': 'Password must be at least 8 characters long.'
                })
            
            # Set the new password
            user.set_password(new_password1)
            user.save()
            
            messages.success(request, 'Your password has been reset successfully. You can now login with your new password.')
            return redirect('login')
        
        return render(request, 'password_reset_confirm.html')
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'Password reset link is invalid.')
        return redirect('login')

