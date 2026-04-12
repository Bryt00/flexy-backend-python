from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Wallet, Transaction

@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ('user', 'balance', 'currency')

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('id', 'amount', 'type', 'status')
