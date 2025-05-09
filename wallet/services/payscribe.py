import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class PayscribeService:
    BASE_URL = settings.PAYSCRIBE_BASE_URL
    
    @classmethod
    def create_virtual_account(cls, user_email, wallet_id):
        """3.1 Wallet Creation"""
        payload = {
            "customer_email": user_email,
            "wallet_id": wallet_id,
            "is_permanent": True
        }
        return cls._make_request("/virtual-accounts", payload)

    @classmethod
    def process_withdrawal(cls, amount, bank_details, reference, narration=""):
        """3.3 Withdrawal"""
        payload = {
            "amount": amount,
            "bank_code": bank_details['bank_code'],
            "account_number": bank_details['account_number'],
            "account_name": bank_details['account_name'],
            "reference": reference,
            "narration": narration
        }
        return cls._make_request("/payouts/bank", payload)

    @classmethod
    def buy_airtime(cls, phone, amount, network):
        """3.6 Airtime Purchase"""
        payload = {
            "phone_number": phone,
            "amount": amount,
            "network": network.upper()
        }
        return cls._make_request("/vas/airtime", payload)

    @classmethod
    def buy_data(cls, phone, plan_code, network):
        """3.6 Data Purchase"""
        payload = {
            "phone_number": phone,
            "plan_code": plan_code,
            "network": network.upper()
        }
        return cls._make_request("/vas/data", payload)

    @classmethod
    def _make_request(cls, endpoint, payload):
        headers = {
            "Authorization": f"Bearer {settings.PAYSCRIBE_API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(
                f"{cls.BASE_URL}{endpoint}",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Payscribe API error: {str(e)}")
            return False, str(e)