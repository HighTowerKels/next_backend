from django.urls import path
from .views import (
    RegisterView, CustomTokenObtainPairView, WalletView,
    DepositWebhookView, WithdrawalView, TransferView,
    LoginView, EmailVerificationView, ForgotPasswordView, 
    ResetPasswordView, AirtimeView, DataView
)

urlpatterns = [
    # Authentication URLs
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/verify-email/<str:uidb64>/<str:token>/', 
         EmailVerificationView.as_view(), name='verify-email'),
    path('auth/forgot-password/', 
         ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/<str:uidb64>/<str:token>/',
         ResetPasswordView.as_view(), name='reset-password'),

    # Wallet URLs
    path('wallet/', WalletView.as_view(), name='wallet-detail'),
    path('wallet/deposit/webhook/', 
         DepositWebhookView.as_view(), name='deposit-webhook'),
    path('wallet/withdraw/', WithdrawalView.as_view(), name='withdraw'),
    path('wallet/transfer/', TransferView.as_view(), name='transfer'),

    # VTU URLs
    path('airtime/buy/', AirtimeView.as_view(), name='buy-airtime'),
    path('data/buy/', DataView.as_view(), name='buy-data'),
]