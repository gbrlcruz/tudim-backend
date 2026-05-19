from tudim.ai.extractors import extract_habit_log
from tudim.db.repositories.habit_repo import match_habit_by_aliases
from tudim.domain import entities as domain
from tudim.domain.unit_of_work import UnitOfWork
from tudim.pipeline.types import Action


async def handle_habit_log(
    uow: UnitOfWork, user: domain.User, action: Action, raw_message: str
) -> str:
    active = await uow.habits.list_active(user.id)
    if not active:
        return "Você ainda não tem hábitos ativos 🐹 (manda 'novo hábito' pra criar)"

    matched = match_habit_by_aliases(active, action.raw_text)
    extracted = await extract_habit_log(
        text=action.raw_text, user=user, active_habits=active
    )

    if matched is None:
        if extracted.habit_id is None:
            return "Hmm, não identifiquei qual hábito é esse 🐹"
        matched = next((h for h in active if h.id == extracted.habit_id), None)
        if matched is None:
            return "Hmm, não achei esse hábito 🐹"

    await uow.habits.log_check_in(
        habit_id=matched.id,
        user_id=user.id,
        occurred_at=extracted.occurred_at,
        details=extracted.details,
    )
    await uow.commit()

    streak = await uow.habits.compute_streak(matched.id, user.timezone)
    streak_str = f" — {streak} dias seguidos 🔥" if streak > 1 else ""
    return f"Marcado: *{matched.name}*{streak_str}"
