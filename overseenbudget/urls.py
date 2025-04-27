"""
URL configuration for overseenbudget project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from home.views import (
    search_page, account_page, expense_page, register, CustomLogoutView, custom_login,
    create_link_token, exchange_public_token, sync_transactions, get_transactions,
    search_transactions, get_calendar_transactions, get_accounts, unlink_account,
    debug_plaid, budget_page, password_reset, password_reset_confirm
)
from home import views as home_views
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

# Redirect root to login if not authenticated
def redirect_to_login(request):
    if request.user.is_authenticated:
        return redirect('account')
    return custom_login(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', redirect_to_login, name='home'),  # Root URL redirects to login or account
    path('search/', login_required(search_page, login_url='/'), name='search'),
    path('search_transactions/', login_required(home_views.search_transactions, login_url='/'), name='search_transactions'),
    path('account/', login_required(account_page, login_url='/'), name='account'),
    path('calendar_transactions/', login_required(home_views.get_calendar_transactions, login_url='/'), name='calendar_transactions'),
    path('expense/', login_required(expense_page, login_url='/'), name='expense'),
    path('budget/', login_required(home_views.budget_page, login_url='/'), name='budget'),
    path('login/', custom_login, name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('plaid/create-link-token/', login_required(home_views.create_link_token, login_url='/'), name='create_link_token'),
    path('plaid/exchange-public-token/', login_required(home_views.exchange_public_token, login_url='/'), name='exchange_public_token'),
    path('plaid/sync-transactions/', login_required(home_views.sync_transactions, login_url='/'), name='sync_transactions'),
    path('plaid/test-link-token/', login_required(home_views.test_link_token, login_url='/'), name='test_link_token'),
    path('plaid/debug/', login_required(home_views.debug_plaid, login_url='/'), name='debug_plaid'),
    path('plaid/get-transactions/', login_required(home_views.get_transactions, login_url='/'), name='get_transactions'),
    path('plaid/get-accounts/', login_required(home_views.get_accounts, login_url='/'), name='get_accounts'),
    path('unlink_account/', login_required(home_views.unlink_account), name='unlink_account'),
    path('password_reset/', password_reset, name='password_reset'),
    path('password_reset_confirm/<str:uidb64>/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
]

