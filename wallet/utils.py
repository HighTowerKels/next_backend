import hmac
import hashlib
from django.conf import settings

def verify_webhook_signature(payload, received_signature):
    """
    Verify Payscribe webhook signature
    """
    secret_key = settings.PAYSCRIBE_WEBHOOK_SECRET.encode('utf-8')
    expected_signature = hmac.new(
        secret_key,
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)