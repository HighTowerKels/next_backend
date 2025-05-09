from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator, MinValueValidator
from decimal import Decimal

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True, validators=[MinLengthValidator(11)])
    username = models.CharField(max_length=30, unique=True)
    
    # Remove these fields from AbstractUser as we're using email as primary identifier
    first_name = None
    last_name = None
    
    USERNAME_FIELD = 'email'  # Use email as the login field
    REQUIRED_FIELDS = ['username', 'phone_number']  # Required when creating superuser
    
    def __str__(self):
        return self.email

    
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    wallet_id = models.CharField(max_length=20, unique=True, editable=False)
    virtual_account_number = models.CharField(max_length=20, blank=True, null=True)
    virtual_bank_name = models.CharField(max_length=50, blank=True, null=True)
    virtual_account_reference = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.wallet_id}"

    def generate_wallet_id(self):
        """Generate a unique wallet ID"""
        import random
        import string
        prefix = "NEXA"
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return f"{prefix}{random_part}"
    def create_transaction(self, **kwargs):
        """Helper method to create transactions"""
        return Transaction.objects.create(wallet=self, **kwargs)
    def save(self, *args, **kwargs):
        if not self.wallet_id:
            self.wallet_id = self.generate_wallet_id()
        super().save(*args, **kwargs)

class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
        TRANSFER = 'TRANSFER', 'Transfer'
        PAYMENT = 'PAYMENT', 'Payment'
        AIRTIME = 'AIRTIME', 'Airtime'
        DATA = 'DATA', 'Data'

    class TransactionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REVERSED = 'REVERSED', 'Reversed'

    wallet = models.ForeignKey('Wallet', on_delete=models.PROTECT, related_name='transactions')
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )
    reference = models.CharField(max_length=100, unique=True)
    narration = models.CharField(max_length=200, blank=True, null=True)
    recipient_wallet = models.ForeignKey(
        'Wallet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transactions'
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['wallet']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.reference} - {self.get_transaction_type_display()} - {self.amount}"
