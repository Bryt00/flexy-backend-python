import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class PaystackService:
    """
    Centralized service for interacting with the Paystack API.
    """
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        if not self.secret_key:
            logger.warning("Paystack Secret Key is not configured in settings.")

    def initialize_transaction(self, email, amount, callback_url=None, metadata=None):
        """
        Initialize a transaction with Paystack.
        :param email: Customer's email address
        :param amount: Amount to charge (will be converted to pesewas/kobo)
        :param callback_url: URL to redirect after payment
        :param metadata: Extra data to be stored with the transaction
        """
        url = f"{self.base_url}/transaction/initialize"
        
        # Paystack expects amount in the smallest currency unit (e.g., pesewas for GHS)
        # We assume the input amount is in standard units (e.g., Cedis)
        amount_kobo = int(float(amount) * 100)
        
        payload = {
            "email": email,
            "amount": amount_kobo,
            "metadata": metadata or {},
        }
        
        if callback_url:
            payload["callback_url"] = callback_url
            
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response_data = response.json()
            if not response_data.get('status'):
                logger.error(f"Paystack Initialize Error: {response_data.get('message')}")
            return response_data
        except Exception as e:
            logger.error(f"Paystack Service Exception (Initialize): {e}")
            return {"status": False, "message": str(e)}

    def verify_transaction(self, reference):
        """
        Verify a transaction with Paystack using its reference.
        """
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response_data = response.json()
            if not response_data.get('status'):
                logger.error(f"Paystack Verify Error: {response_data.get('message')}")
            return response_data
        except Exception as e:
            logger.error(f"Paystack Service Exception (Verify): {e}")
            return {"status": False, "message": str(e)}

    def create_transfer_recipient(self, name, account_number, bank_code, currency="GHS"):
        """
        Create a transfer recipient for payouts/withdrawals.
        """
        url = f"{self.base_url}/transferrecipient"
        payload = {
            "type": "nuban", # Standard for bank accounts
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"Paystack Service Exception (TransferRecipient): {e}")
            return {"status": False, "message": str(e)}

    def initiate_transfer(self, amount, recipient_code, reason="Payout"):
        """
        Initiate a transfer to a recipient.
        """
        url = f"{self.base_url}/transfer"
        payload = {
            "source": "balance",
            "amount": int(float(amount) * 100),
            "recipient": recipient_code,
            "reason": reason
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return response.json()
        except Exception as e:
            logger.error(f"Paystack Service Exception (Transfer): {e}")
            return {"status": False, "message": str(e)}
