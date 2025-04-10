from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.http import HttpResponse


class AccountPageView(LoginRequiredMixin, View):
    login_url = '/login/'  

    def get(self, request):
        return render(request, 'account.html')

def search_page(request):
    return render(request, 'search.html')

def account_page(request):
    return render(request, 'account.html')

def expense_page(request):
    return render(request, 'expense.html')
