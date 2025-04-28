from django.urls import path
from . import views
from django.urls import path
from home.views import (
    search_page, account_page, expense_page, register, CustomLogoutView, custom_login,
    create_link_token, exchange_public_token, sync_transactions, get_transactions,
    search_transactions, get_calendar_transactions, get_accounts, unlink_account,
    debug_plaid, budget_page, password_reset, password_reset_confirm, delete_account
)
from home import views as home_views
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

urlpatterns = [
    path('', views.account_page, name='account'),
    path('search/', views.search_page, name='search'),
    path('search_transactions/', views.search_transactions, name='search_transactions'),
    path('expense/', views.expense_page, name='expense'),
    path('budget/', views.budget_page, name='budget'),
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('create_link_token/', views.create_link_token, name='create_link_token'),
    path('test_link_token/', views.test_link_token, name='test_link_token'),
    path('exchange_public_token/', views.exchange_public_token, name='exchange_public_token'),
    path('sync_transactions/', views.sync_transactions, name='sync_transactions'),
    path('get_transactions/', views.get_transactions, name='get_transactions'),
    path('debug_plaid/', views.debug_plaid, name='debug_plaid'),
    path('delete-account/', views.delete_account, name='delete_account'),
    ]
