from rest_framework import serializers
from .models import Wallet, Transaction

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class WalletSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Wallet
        fields = ('id', 'user', 'balance', 'currency', 'transactions', 'updated_at')
        read_only_fields = ('id', 'user', 'balance', 'updated_at')
