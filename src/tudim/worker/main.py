import base64
import json
import logging
from fastapi import FastAPI, HTTPException, Request, Response

from tudim.db.session import get_session
from tudim.pubsub.publisher import IncomingMessageEvent
from tudim.pipeline.process import process_message

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tudim.worker")

app = FastAPI()


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.post("/pubsub/push")
async def pubsub_push(request: Request):
    envelope = await request.json()
    msg = envelope.get("message", {})
    raw = base64.b64decode(msg["data"]).decode("utf-8")
    ev = IncomingMessageEvent.model_validate_json(raw)

    try:
        async with get_session() as session:
            await process_message(session, ev)
    except Exception:
        log.exception("process failed sid=%s", ev.message_sid)
        raise HTTPException(status_code=500, detail="retry")

    return Response(status_code=204)  # ack
