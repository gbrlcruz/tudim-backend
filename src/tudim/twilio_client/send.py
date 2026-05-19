import logging

from twilio.rest import Client

from tudim.config import settings

log = logging.getLogger("tudim.twilio")

_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def send_text(to_e164: str, body: str) -> str:
    """Send a WhatsApp text. `to_e164` is bare E.164 (e.g. "+5521999999999")."""
    msg = _client.messages.create(
        from_=settings.twilio_whatsapp_from,
        to=f"whatsapp:{to_e164}",
        body=body,
    )
    log.info("sent message sid=%s to=%s", msg.sid, to_e164)
    return msg.sid
