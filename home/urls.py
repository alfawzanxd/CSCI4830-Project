from django.urls import path
from . import views

urlpatterns = [
    path('expense/', views.expense_view, name='expense'),
    path('account/', views.account_view, name='account'),
]

