import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tudim.api.schemas.auth import RequestOtpIn, RequestOtpOut
from tudim.db.models import OTPSession
from tudim.db.session import get_session
from tudim.auth.utils import hash_otp
from tudim.twilio_client.send import send_text

router = APIRouter(prefix="/auth")


@router.post("/request-otp", response_model=RequestOtpOut)
async def request_otp(payload: RequestOtpIn, session: AsyncSession = Depends(get_session)):
    code = f"{secrets.randbelow(1000000):06d}"
    otp = OTPSession(
        phone_number=payload.phone_number,
        code_hash=hash_otp(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session.add(otp)
    await session.commit()
    await session.refresh(otp)

    await send_text(payload.phone_number, f"Seu código do Tudim: {code} 🐹")
    return RequestOtpOut(session_id=str(otp.id))
