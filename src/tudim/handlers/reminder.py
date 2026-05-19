from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from tudim.ai.extractors import extract_reminder
from tudim.domain import entities as domain
from tudim.domain.unit_of_work import UnitOfWork
from tudim.pipeline.types import Action


async def handle_reminder(
    uow: UnitOfWork, user: domain.User, action: Action, raw_message: str
) -> str:
    extracted = await extract_reminder(text=action.raw_text, user=user)

    if extracted.scheduled_for < datetime.now(timezone.utc) + timedelta(minutes=1):
        return "Hmm, esse horário tá no passado 🐹 manda outro?"

    reminder = await uow.reminders.create(
        user_id=user.id,
        content=extracted.content,
        scheduled_for=extracted.scheduled_for,
    )
    await uow.commit()

    local = reminder.scheduled_for.astimezone(ZoneInfo(user.timezone))
    return f"Combinado, vou te lembrar em {local.strftime('%d/%m às %H:%M')} 🐹"
