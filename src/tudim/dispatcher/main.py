import logging
from fastapi import FastAPI, Response
from sqlalchemy import text

from tudim.db.session import get_session
from tudim.twilio_client.send import send_text

log = logging.getLogger("tudim.dispatcher")
app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/dispatch")
async def dispatch():
    async with get_session() as session:
        # Claim due reminders atomically
        result = await session.execute(text("""
            UPDATE reminders
            SET status = 'sending', updated_at = NOW()
            WHERE id IN (
              SELECT id FROM reminders
              WHERE status = 'pending'
                AND scheduled_for <= NOW()
                AND deleted_at IS NULL
              ORDER BY scheduled_for
              LIMIT 100
              FOR UPDATE SKIP LOCKED
            )
            RETURNING id, user_id, content
        """))
        reminders = list(result.mappings())
        await session.commit()

    for rem in reminders:
        async with get_session() as session:
            user = await session.get(User, rem["user_id"])
            try:
                await send_text(user.phone_number, f"⏰ {rem['content']}")
                await session.execute(
                    text(
                        "UPDATE reminders SET status='sent', sent_at=NOW() WHERE id=:id"
                    ),
                    {"id": rem["id"]},
                )
            except Exception:
                log.exception("send failed for reminder %s", rem["id"])
                # Leave it in 'sending'. A sweeper (or manual reset) can re-pending after 5 min.
            await session.commit()

    return Response(status_code=204)
