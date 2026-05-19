import logging
from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from tudim.config import settings
from tudim.db.session import get_session
from tudim.handlers.user import upsert_user
from tudim.pubsub.publisher import IncomingMessageEvent, publish_incoming
from tudim.twilio_client.signature import verify_twilio_signature
from tudim.twilio_client.send import send_text
from tudim.api.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("tudim.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("tudim-api starting 🐹")
    yield
    log.info("tudim-api bye 🐹")


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.post("/webhooks/whatsapp")
async def receive_whatsapp(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    MessageSid: str = Form(...),
    NumMedia: int = Form(0),
):
    form = await request.form()
    if not verify_twilio_signature(request, dict(form)):
        raise HTTPException(403, "bad signature")

    ev = IncomingMessageEvent(
        message_sid=form["MessageSid"],
        from_e164=form["From"].removeprefix("whatsapp:"),
        body=form.get("Body", ""),
        num_media=int(form.get("NumMedia", 0)),
        received_at=time.time(),
    )
    await publish_incoming(ev)
    return Response(status_code=204)
