from datetime import datetime, timezone

from tudim.domain import entities as domain
from tudim.domain.unit_of_work import UnitOfWork


def detect_command(msg: str) -> str | None:
    norm = msg.strip().lower()
    if (
        norm in {"desfaz", "desfazer"}
        or norm.startswith("apaga o último")
        or norm.startswith("apaga a última")
    ):
        return "undo"
    if norm in {"ajuda", "menu", "help", "?"}:
        return "help"
    if norm == "lista" or norm.startswith("minhas notas"):
        return "list"
    if norm == "apaga tudo":
        return "wipe_request"
    if norm == "sim, apaga tudo":
        return "wipe_confirm"
    return None


async def handle_command(
    uow: UnitOfWork, user: domain.User, command: str, raw_message: str
) -> str:
    if command == "help":
        return _help_message()

    if command == "undo":
        return await _undo_last_note(uow, user)

    if command == "list":
        notes = await uow.notes.list_for_user(user.id, limit=5)
        if not notes:
            return "Você ainda não tem notas 🐹"
        return "\n".join(f"• {n.content}" for n in notes)

    if command == "wipe_request":
        await uow.users.set_pending_destructive(user.id, "wipe", ttl_minutes=5)
        await uow.commit()
        return (
            "⚠️ Isso apaga *todas* suas notas, hábitos e lembretes.\n"
            "Manda 'sim, apaga tudo' nos próximos 5 minutos pra confirmar."
        )

    if command == "wipe_confirm":
        return await _confirm_and_wipe(uow, user)

    return "Comando não reconhecido 🐹"


async def _undo_last_note(uow: UnitOfWork, user: domain.User) -> str:
    last = await uow.notes.get_last(user.id)
    if last is None:
        return "Não tem nada pra desfazer 🐹"
    await uow.notes.soft_delete(last.id)
    await uow.commit()
    return f"Apaguei a última nota: _{last.content}_ 🐹"


async def _confirm_and_wipe(uow: UnitOfWork, user: domain.User) -> str:
    fresh = await uow.users.get_by_phone(user.phone_number)
    now = datetime.now(timezone.utc)
    if (
        fresh is None
        or fresh.pending_destructive_action != "wipe"
        or fresh.pending_destructive_expires_at is None
        or fresh.pending_destructive_expires_at < now
    ):
        return "Tempo expirou ou não havia confirmação pendente 🐹 manda 'apaga tudo' de novo."

    await uow.notes.wipe_for_user(user.id)
    await uow.habits.wipe_for_user(user.id)
    await uow.reminders.wipe_for_user(user.id)
    await uow.users.clear_pending_destructive(user.id)
    await uow.commit()
    return "Pronto, apaguei tudo 🐹 começando do zero."


def _help_message() -> str:
    return (
        "*Tudim — o que eu sei fazer 🐹*\n\n"
        "• Anota qualquer coisa que você manda (com tags automáticas)\n"
        '• Registra hábitos: "corri 30min"\n'
        '• Cria lembretes: "me lembra de ligar pra mãe amanhã às 19h"\n'
        '• Responde perguntas: "o que anotei essa semana?"\n\n'
        "*Comandos:*\n"
        "• `desfaz` — apaga a última anotação\n"
        "• `lista` — mostra as 5 notas mais recentes\n"
        "• `apaga tudo` — limpa toda sua conta (requer confirmação)\n"
        "• `ajuda` — mostra essa mensagem"
    )
