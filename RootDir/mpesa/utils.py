pythonimport base64
import logging
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"


def _get_base_url() -> str:
    return (
        SANDBOX_BASE_URL
        if settings.MPESA_ENVIRONMENT == "sandbox"
        else PRODUCTION_BASE_URL
    )


def get_access_token() -> str | None:
    """Fetch OAuth access token from Safaricom."""
    url = f"{_get_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(
            url,
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as e:
        logger.error("Failed to get M-Pesa access token: %s", e)
        return None


def generate_password() -> tuple[str, str]:
    """
    Returns (password, timestamp).
    Password = base64(shortcode + passkey + timestamp)
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def initiate_stk_push(
    phone_number: str,
    amount: int,
    account_reference: str,
    transaction_desc: str,
) -> dict:
    """
    Trigger STK push to the given phone number.

    Args:
        phone_number: Format 2547XXXXXXXX (no + prefix)
        amount: Integer amount in KES
        account_reference: Shown on customer's phone
        transaction_desc: Short description

    Returns:
        Safaricom API response dict, or dict with 'error' key on failure.
    """
    access_token = get_access_token()
    if not access_token:
        return {"error": "Could not obtain access token"}

    password, timestamp = generate_password()
    url = f"{_get_base_url()}/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error("STK push failed: %s", e)
        return {"error": str(e)}
