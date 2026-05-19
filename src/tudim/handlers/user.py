import logging

from tudim.domain import entities as domain
from tudim.domain.unit_of_work import UnitOfWork

log = logging.getLogger("tudim.handlers.user")


async def upsert_user(uow: UnitOfWork, phone_e164: str) -> tuple[domain.User, bool]:
    user = await uow.users.get_by_phone(phone_e164)
    if user is not None:
        await uow.users.touch_last_inbound(user.id)
        await uow.commit()
        return user, False

    user = await uow.users.create(phone_e164)
    await uow.users.touch_last_inbound(user.id)
    await uow.commit()
    log.info("created user id=%s phone=%s", user.id, phone_e164)
    return user, True


async def check_rate_limit(uow: UnitOfWork, user_id, daily_limit: int = 100) -> bool:
    ok = await uow.users.try_increment_daily_count(user_id, daily_limit=daily_limit)
    await uow.commit()
    return ok


def welcome_message() -> str:
    return (
        "Oi! Eu sou o Tudim 🐹\n"
        "Manda qualquer coisa que você quer lembrar e eu organizo pra você.\n"
        "Manda 'ajuda' a qualquer momento pra ver o que sei fazer."
    )
