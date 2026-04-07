# services/phonepe_service.py
# Separate service layer - handles ALL PhonePe API communication

import secrets
import time
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PhonePeService:
    """
    Handles all communication with the PhonePe Payment Gateway API.
    Keeps API logic completely separate from Django views and business logic.
    """

    TOKEN_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token"
    PAYMENT_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"
    STATUS_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{merchant_order_id}/status"

    @staticmethod
    def get_access_token() -> str:
        """Fetch a fresh OAuth2 access token from PhonePe."""
        payload = {
            "client_version": 1,
            "grant_type": "client_credentials",
            "client_id": settings.PHONEPE_CLIENT_ID,
            "client_secret": settings.PHONEPE_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(
                PhonePeService.TOKEN_URL,
                data=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise ValueError("access_token missing in PhonePe response")
            return token

        except requests.exceptions.Timeout:
            logger.error("PhonePe token request timed out")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error("PhonePe token HTTP error: %s | body: %s", e, response.text)
            raise

    @staticmethod
    def initiate_payment(merchant_order_id: str, amount_paise: int, access_token: str, customer: "Customers") -> dict:
        """
        Create a payment order on PhonePe.
        amount_paise: Amount in paise (₹1 = 100 paise)
        """
        redirect_url = f"{settings.FRONTEND_URL}/payment-status?transactionId={merchant_order_id}"

        payload = {
            "amount": amount_paise,
            "expireAfter": 1200,  # 20 minutes
            "merchantOrderId": merchant_order_id,
            "metaInfo": {
                "udf1": str(customer.user.id),
                "udf2": customer.name or "",
                "udf3": customer.mobileno or "",
                "udf4": customer.city or "",
                "udf5": customer.state or "",
            },
            "paymentFlow": {
                "type": "PG_CHECKOUT",
                "message": "Order payment",
                "merchantUrls": {
                    "redirectUrl": redirect_url,
                    # Uncomment when you have a public webhook URL:
                    # "callbackUrl": settings.PHONEPE_CALLBACK_URL,
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"O-Bearer {access_token}",
        }

        try:
            response = requests.post(
                PhonePeService.PAYMENT_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error("PhonePe payment request timed out for order: %s", merchant_order_id)
            raise
        except requests.exceptions.HTTPError as e:
            logger.error("PhonePe payment HTTP error: %s | body: %s", e, response.text)
            raise

    @staticmethod
    def get_order_status(merchant_order_id: str, access_token: str) -> dict:
        """Check the status of an existing PhonePe order."""
        url = PhonePeService.STATUS_URL.format(merchant_order_id=merchant_order_id)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"O-Bearer {access_token}",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error("PhonePe status request timed out for order: %s", merchant_order_id)
            raise
        except requests.exceptions.HTTPError as e:
            logger.error("PhonePe status HTTP error: %s | body: %s", e, response.text)
            raise