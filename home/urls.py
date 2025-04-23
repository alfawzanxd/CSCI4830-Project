from django.urls import path
from . import views

urlpatterns = [
    path('', views.account_page, name='account'),
    path('search/', views.search_page, name='search'),
    path('search_transactions/', views.search_transactions, name='search_transactions'),
    path('expense/', views.expense_page, name='expense'),
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('create_link_token/', views.create_link_token, name='create_link_token'),
    path('test_link_token/', views.test_link_token, name='test_link_token'),
    path('exchange_public_token/', views.exchange_public_token, name='exchange_public_token'),
    path('sync_transactions/', views.sync_transactions, name='sync_transactions'),
    path('get_transactions/', views.get_transactions, name='get_transactions'),
    path('debug_plaid/', views.debug_plaid, name='debug_plaid'),
]

