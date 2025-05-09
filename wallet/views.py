from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction as db_transaction
from django.contrib.auth import get_user_model
import json
import logging
import requests
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
import uuid

from .models import Wallet, Transaction
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    WalletSerializer,
    TransactionSerializer,
    DepositWebhookSerializer,
    WithdrawalSerializer,
    TransferSerializer
)
from .services.payscribe import PayscribeService
from .services.transactions import TransactionService
from .utils import verify_webhook_signature

User = get_user_model()
logger = logging.getLogger(__name__)

# ==================== AUTHENTICATION VIEWS ====================
class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with db_transaction.atomic():
            # Create user
            user = serializer.save()
            
            # Create wallet
            wallet = Wallet.objects.create(
                user=user,
                wallet_id=f"NEXA{str(uuid.uuid4())[:8].upper()}"
            )

            response_data = {
                'user': UserSerializer(user).data,
                'wallet': WalletSerializer(wallet).data
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token view that returns user data with tokens
    """
    serializer_class = CustomTokenObtainPairSerializer
class EmailVerificationView(APIView):
    """
    Handle email verification for new users
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            if default_token_generator.check_token(user, token):
                user.is_verified = True
                user.save()
                return Response(
                    {"message": "Email successfully verified"},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Invalid verification link"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Invalid verification link"},
                status=status.HTTP_400_BAD_REQUEST
            )

class ForgotPasswordView(APIView):
    """
    Handle password reset request
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            user = User.objects.get(email=email)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            current_site = get_current_site(request)
            
            # Create password reset link
            reset_url = f"{current_site.domain}/reset-password/{uid}/{token}"
            
            # Send email
            email_context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': current_site.name,
            }
            
            email_body = render_to_string('wallet/password_reset_email.html', email_context)
            
            send_mail(
                'Password Reset Request',
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            return Response(
                {"message": "Password reset instructions sent to your email"},
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return Response(
                {"error": "Failed to process password reset request"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResetPasswordView(APIView):
    """
    Handle password reset
    """
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                new_password = request.data.get('new_password')
                if not new_password:
                    return Response(
                        {"error": "New password is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                user.set_password(new_password)
                user.save()
                return Response(
                    {"message": "Password successfully reset"},
                    status=status.HTTP_200_OK
                )
            
            return Response(
                {"error": "Invalid reset link"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return Response(
                {"error": "Failed to reset password"},
                status=status.HTTP_400_BAD_REQUEST
            )

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            if not email or not password:
                return Response(
                    {'error': 'Email and password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(email=email)

            if not user.check_password(password):
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username
                }
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response(
                {'error': 'Login failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# ==================== WALLET VIEWS ====================
class WalletView(APIView):
    """
    Retrieve wallet details for authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)
        return Response(WalletSerializer(wallet).data)

# ==================== TRANSACTION VIEWS ====================
@method_decorator(csrf_exempt, name='dispatch')
class DepositWebhookView(APIView):
    """
    Handles deposit webhooks from Payscribe
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Verify webhook signature
            raw_body = request.body
            received_signature = request.headers.get('X-Payscribe-Signature', '')
            
            if not verify_webhook_signature(raw_body, received_signature):
                logger.warning("Invalid webhook signature")
                return Response(
                    {"status": "error", "message": "Invalid signature"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate and process webhook data
            data = json.loads(raw_body.decode('utf-8'))
            serializer = DepositWebhookSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            
            wallet_id = serializer.validated_data['wallet_id']
            amount = serializer.validated_data['amount']
            reference = serializer.validated_data['reference']
            
            try:
                wallet = Wallet.objects.get(wallet_id=wallet_id)
                txn = TransactionService.create_deposit(
                    wallet=wallet,
                    amount=amount,
                    reference=reference,
                    metadata={
                        "source": "virtual_account",
                        "webhook_data": data
                    }
                )
                
                logger.info(f"Deposit processed for wallet {wallet_id}. Amount: {amount}")
                return Response(TransactionSerializer(txn).data)
            
            except Wallet.DoesNotExist:
                logger.error(f"Wallet not found: {wallet_id}")
                return Response(
                    {"status": "error", "message": "Wallet not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class WithdrawalView(APIView):
    """
    Handles withdrawal requests to external bank accounts
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
            serializer = WithdrawalSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            amount = serializer.validated_data['amount']
            bank_details = {
                'bank_code': serializer.validated_data['bank_code'],
                'account_number': serializer.validated_data['account_number'],
                'account_name': serializer.validated_data['account_name']
            }
            narration = serializer.validated_data.get('narration', '')
            
            # Create withdrawal transaction
            txn = TransactionService.create_withdrawal(
                wallet=wallet,
                amount=amount,
                metadata={
                    "bank_details": bank_details,
                    "narration": narration
                }
            )
            
            # Process withdrawal through Payscribe
            success, response = PayscribeService.process_withdrawal(
                amount=amount,
                bank_details=bank_details,
                reference=txn.reference,
                narration=narration
            )
            
            if success:
                TransactionService.complete_withdrawal(txn)
                return Response(TransactionSerializer(txn).data)
            else:
                TransactionService.fail_withdrawal(txn, response)
                return Response(
                    {"status": "error", "message": response},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except ValueError as e:  # For business logic errors
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Withdrawal processing error: {str(e)}")
            return Response(
                {"status": "error", "message": "Withdrawal processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TransferView(APIView):
    """
    Handles wallet-to-wallet transfers
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            sender_wallet = Wallet.objects.get(user=request.user)
            serializer = TransferSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            amount = serializer.validated_data['amount']
            recipient_wallet_id = serializer.validated_data['recipient_wallet_id']
            narration = serializer.validated_data.get('narration', '')
            
            try:
                recipient_wallet = Wallet.objects.get(wallet_id=recipient_wallet_id)
                
                # Prevent self-transfer
                if sender_wallet == recipient_wallet:
                    return Response(
                        {"status": "error", "message": "Cannot transfer to your own wallet"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Process transfer through TransactionService
                outgoing_txn, incoming_txn = TransactionService.create_transfer(
                    sender_wallet=sender_wallet,
                    recipient_wallet=recipient_wallet,
                    amount=amount,
                    metadata={
                        "narration": narration,
                        "initiator": str(request.user.id)
                    }
                )
                
                return Response({
                    "status": "success",
                    "outgoing_transaction": TransactionSerializer(outgoing_txn).data,
                    "incoming_transaction": TransactionSerializer(incoming_txn).data
                })
            
            except Wallet.DoesNotExist:
                return Response(
                    {"status": "error", "message": "Recipient wallet not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except ValueError as e:  # For business logic errors
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Transfer processing error: {str(e)}")
            return Response(
                {"status": "error", "message": "Transfer processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TransactionHistoryView(APIView):
    """
    Retrieves transaction history for authenticated user's wallet
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)
        transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
        return Response(TransactionSerializer(transactions, many=True).data)
    
# ==================== VTU (VTU) VIEWS ====================

class AirtimeView(APIView):
    """3.6 Airtime Purchase"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        wallet = Wallet.objects.get(user=request.user)
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        network = request.data.get('network')

        if wallet.balance < amount:
            return Response(
                {"error": "Insufficient balance"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, response = PayscribeService.buy_airtime(phone, amount, network)
        
        if success:
            txn = TransactionService.create_vas_transaction(
                wallet=wallet,
                amount=amount,
                service_type='AIRTIME',
                metadata={
                    "phone": phone,
                    "network": network,
                    "payscribe_response": response
                }
            )
            return Response(TransactionSerializer(txn).data)
        
        return Response(
            {"error": response},
            status=status.HTTP_400_BAD_REQUEST
        )

class DataView(APIView):
    """3.6 Data Purchase"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        wallet = Wallet.objects.get(user=request.user)
        phone = request.data.get('phone')
        plan_code = request.data.get('plan_code')
        network = request.data.get('network')
        amount = request.data.get('amount')  # Get from plan_code lookup

        if wallet.balance < amount:
            return Response(
                {"error": "Insufficient balance"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, response = PayscribeService.buy_data(phone, plan_code, network)
        
        if success:
            txn = TransactionService.create_vas_transaction(
                wallet=wallet,
                amount=amount,
                service_type='DATA',
                metadata={
                    "phone": phone,
                    "plan": plan_code,
                    "network": network,
                    "payscribe_response": response
                }
            )
            return Response(TransactionSerializer(txn).data)
        
        return Response(
            {"error": response},
            status=status.HTTP_400_BAD_REQUEST
        )
# ==================== END OF FILE ====================