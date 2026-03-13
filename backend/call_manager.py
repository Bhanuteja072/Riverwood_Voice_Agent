from urllib.parse import quote

from twilio.rest import Client
from .config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

_client = None

def _get_client() -> Client:
    global _client
    if _client is None:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
            raise RuntimeError(
                "Twilio credentials missing. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env"
            )
        _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _client


def place_outbound_call(
    customer_phone: str,
    customer_name: str,
    webhook_base_url: str
) -> str:
    """
    Place a real outbound call to customer_phone.
    Returns the Twilio call SID.
    
    webhook_base_url example: https://abc123.ngrok.io
    """
    webhook_url = (
        f"{webhook_base_url}/twilio-answer"
        f"?customer_name={quote(customer_name, safe='')}"
    )

    call = _get_client().calls.create(
        to=customer_phone,
        from_=TWILIO_PHONE_NUMBER,
        url=webhook_url,
        method="POST",
        timeout=30,           # seconds to wait for customer to pick up
        machine_detection="Enable"  # detects voicemail automatically
    )
    return call.sid


def get_call_status(call_sid: str) -> str:
    """Returns: queued, ringing, in-progress, completed, busy, failed, no-answer"""
    call = _get_client().calls(call_sid).fetch()
    return call.status