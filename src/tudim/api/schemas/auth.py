from pydantic import BaseModel


class RequestOtpIn(BaseModel):
    phone_number: str


class RequestOtpOut(BaseModel):
    session_id: str
    expires_in: int = 300
