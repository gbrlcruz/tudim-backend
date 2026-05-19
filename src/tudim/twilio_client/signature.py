from fastapi import Request
from twilio.request_validator import RequestValidator

from tudim.config import settings

_validator = RequestValidator(settings.twilio_auth_token)


def verify_twilio_signature(request: Request, form: dict[str, str]) -> bool:
    signature = request.headers.get("X-Twilio-Signature", "")

    if settings.public_base_url:
        url = settings.public_base_url.rstrip("/") + request.url.path
        if request.url.query:
            url = f"{url}?{request.url.query}"
    else:
        url = str(request.url)

    return _validator.validate(url, form, signature)