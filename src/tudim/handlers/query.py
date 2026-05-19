from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from tudim.ai.extractors import extract_query, QueryFilter
from tudim.domain import entities as domain
from tudim.domain.unit_of_work import UnitOfWork
from tudim.pipeline.types import Action


async def handle_query(
    uow: UnitOfWork, user: domain.User, action: Action, raw_message: str
) -> str:
    tag_names = await uow.tags.list_names_for_user(user.id)
    habit_names = await uow.habits.list_active_names(user.id)

    qf = await extract_query(
        text=action.raw_text,
        user=user,
        existing_tags=tag_names,
        active_habits=habit_names,
    )

    if qf.type == "notes":
        return await _query_notes(uow, user, qf)
    if qf.type == "habits":
        return await _query_habits(uow, user)
    if qf.type == "reminders":
        return await _query_reminders(uow, user)
    return "Não entendi bem o que você quer consultar 🐹"


async def _query_notes(uow: UnitOfWork, user: domain.User, qf: QueryFilter) -> str:
    from_dt, to_dt = _period_to_range(qf.period, user.timezone)

    if qf.q:
        notes = await uow.notes.search_text(user.id, qf.q, limit=qf.limit or 5)
    else:
        tag_id = None
        if qf.tag:
            tags = await uow.tags.ensure_many(user.id, [qf.tag])
            tag_id = tags[0].id if tags else None
        notes = await uow.notes.list_for_user(
            user.id,
            tag_id=tag_id,
            from_dt=from_dt,
            to_dt=to_dt,
            limit=qf.limit or 5,
        )

    if not notes:
        return "Não achei nenhuma nota com esses critérios 🐹"

    lines = []
    for n in notes[:5]:
        local = n.occurred_at.astimezone(ZoneInfo(user.timezone)).strftime(
            "%d/%m %H:%M"
        )
        lines.append(f"• [{local}] {n.content}")
    extra = f"\n…e mais {len(notes) - 5}" if len(notes) > 5 else ""
    return "\n".join(lines) + extra


async def _query_habits(uow: UnitOfWork, user: domain.User) -> str:
    habits = await uow.habits.list_active(user.id)
    if not habits:
        return "Você ainda não tem hábitos ativos 🐹"
    lines = []
    for h in habits:
        streak = await uow.habits.compute_streak(h.id, user.timezone)
        lines.append(f"• *{h.name}* — {streak} dia(s) seguidos")
    return "\n".join(lines)


async def _query_reminders(uow: UnitOfWork, user: domain.User) -> str:
    rems = await uow.reminders.list_pending_for_user(user.id)
    if not rems:
        return "Nenhum lembrete pendente 🐹"
    lines = []
    for r in rems[:5]:
        local = r.scheduled_for.astimezone(ZoneInfo(user.timezone)).strftime(
            "%d/%m %H:%M"
        )
        lines.append(f"• [{local}] {r.content}")
    return "\n".join(lines)


def _period_to_range(period, tz):
    if not period:
        return None, None
    now = datetime.now(ZoneInfo(tz))
    if period == "today":
        return (
            now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(
                timezone.utc
            ),
            None,
        )
    if period == "week":
        return (now - timedelta(days=7)).astimezone(timezone.utc), None
    if period == "month":
        return (now - timedelta(days=30)).astimezone(timezone.utc), None
    return None, None
