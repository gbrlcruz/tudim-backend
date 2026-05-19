import time
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from tudim.ai import classify, Intent
from tudim.handlers import (
    upsert_user,
    handle_note,
    handle_habit_log,
    handle_reminder,
    handle_query,
    handle_command,
)
from tudim.handlers.commands import detect_command
from tudim.handlers.rate_limit import check_rate_limit, increment_message_count
from tudim.pubsub.publisher import IncomingMessageEvent
from tudim.twilio_client.send import send_text


async def process_message(session: AsyncSession, ev: IncomingMessageEvent):
    user, _ = await upsert_user(session, ev.from_e164)

    if not await check_rate_limit(session, user.id):
        await send_text(ev.from_e164, "Eita, hoje você já mandou bastante coisa! 🐹")
        return

    # Shortcut: detect command keywords before paying for an AI call
    if cmd := detect_command(ev.body):
        reply = await handle_command(session, user, cmd, ev.body)
        await send_text(ev.from_e164, reply)
        return

    habits = await list_active_habit_names(session, user.id)
    tags = await list_tag_names(session, user.id)
    now_local = datetime.now(ZoneInfo(user.timezone))

    result = await classify(
        message=ev.body,
        habits=habits,
        tags=tags,
        now=now_local.isoformat(),
        tz=user.timezone,
    )

    replies = []
    for action in result.actions:
        try:
            reply = await dispatch_action(session, user, action, ev.body)
        except Exception as e:
            log.exception("action failed intent=%s", action.intent)
            replies.append("Algo aí não deu certo 🐹")
            continue
        if reply:
            replies.append(reply)

    if replies:
        await send_text(ev.from_e164, "\n".join(replies))

    await increment_message_count(session, user.id)


async def dispatch_action(session, user, action, raw_text):
    match action.intent:
        case Intent.NOTE:
            return await handle_note(session, user, action, raw_text)
        case Intent.HABIT_LOG:
            return await handle_habit_log(session, user, action, raw_text)
        case Intent.REMINDER_CREATE:
            return await handle_reminder(session, user, action, raw_text)
        case Intent.QUERY:
            return await handle_query(session, user, action, raw_text)
        case Intent.CASUAL_CHAT:
            return action.casual_reply or "🐹"
        case _:
            return "Eita, não entendi 😅 pode reformular?"
