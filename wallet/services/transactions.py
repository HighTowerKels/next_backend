from django.db import transaction
from ..models import Transaction, Wallet
import uuid
import logging

logger = logging.getLogger(__name__)

class TransactionService:
    
    @staticmethod
    def generate_reference(prefix='TXN'):
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    def create_deposit(cls, wallet, amount, reference=None, metadata=None):
        """3.2 Top-Up"""
        if not reference:
            reference = cls.generate_reference('DEP')
        
        with transaction.atomic():
            txn = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='DEPOSIT',
                status='SUCCESS',
                reference=reference,
                metadata=metadata or {}
            )
            wallet.balance += amount
            wallet.save()
            return txn

    @classmethod
    def create_vas_transaction(cls, wallet, amount, service_type, metadata):
        """3.6 Airtime/Data"""
        reference = cls.generate_reference(service_type[:3].upper())
        
        with transaction.atomic():
            txn = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=service_type,
                status='SUCCESS',
                reference=reference,
                metadata=metadata
            )
            wallet.balance -= amount
            wallet.save()
            return txn