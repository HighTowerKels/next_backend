from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Wallet, Transaction
from django.conf import settings

User = get_user_model()

# ==================== USER SERIALIZERS ====================
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'phone_number', 'password')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'phone_number': {'required': True},
        }
    
    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address")
        return value
    
    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number should contain only digits")
        if len(value) < 11:
            raise serializers.ValidationError("Phone number should be at least 11 digits")
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            phone_number=validated_data['phone_number'],
            password=validated_data['password']
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Allow login with either email or phone number
        login = attrs.get('email')  # Default to email
        
        if '@' not in login:
            # If input doesn't contain @, try phone number
            try:
                user = User.objects.get(phone_number=login)
                attrs['email'] = user.email
            except User.DoesNotExist:
                pass
        
        data = super().validate(attrs)
        
        # Add custom response data
        data.update({
            'user': {
                'email': self.user.email,
                'username': self.user.username,
                'phone_number': self.user.phone_number,
            }
        })
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['phone_number'] = user.phone_number
        return token

# ==================== WALLET SERIALIZERS ====================
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('wallet_id', 'balance', 'virtual_account_number', 'virtual_bank_name', 'created_at')
        read_only_fields = fields

# ==================== TRANSACTION SERIALIZERS ====================
class TransactionSerializer(serializers.ModelSerializer):
    transaction_type = serializers.CharField(source='get_transaction_type_display')
    status = serializers.CharField(source='get_status_display')
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'reference',
            'amount',
            'transaction_type',
            'status',
            'narration',
            'recipient_wallet',
            'metadata',
            'created_at'
        ]
        read_only_fields = fields

class DepositWebhookSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    wallet_id = serializers.CharField(max_length=20)
    timestamp = serializers.DateTimeField()
    signature = serializers.CharField(max_length=200)

class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01
    )
    bank_code = serializers.CharField(max_length=10)
    account_number = serializers.CharField(max_length=20)
    account_name = serializers.CharField(max_length=100)
    narration = serializers.CharField(max_length=200, required=False)

class TransferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01
    )
    recipient_wallet_id = serializers.CharField(max_length=20)
    narration = serializers.CharField(max_length=200, required=False)