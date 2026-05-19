from tudim.ai.extractors import extract_note
from tudim.domain import entities as domain
from tudim.domain.unit_of_work import UnitOfWork
from tudim.pipeline.types import Action


async def handle_note(
    uow: UnitOfWork, user: domain.User, action: Action, raw_message: str
) -> str:
    existing_tags = await uow.tags.list_names_for_user(user.id)
    extracted = await extract_note(
        text=action.raw_text, user=user, existing_tags=existing_tags
    )

    tag_objs = await uow.tags.ensure_many(user.id, extracted.tags)
    note = await uow.notes.create(
        user_id=user.id,
        content=action.raw_text,
        raw_message=raw_message,
        occurred_at=extracted.occurred_at,
        confidence=action.confidence,
        tag_ids=[t.id for t in tag_objs],
    )
    await uow.commit()

    if tag_objs:
        return f"Anotei 🐹 tag: *{', '.join(t.name for t in tag_objs)}*"
    return "Anotei 🐹"
