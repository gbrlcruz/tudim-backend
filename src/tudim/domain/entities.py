import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ReminderStatus = Literal["pending", "sending", "sent", "failed", "cancelled"]


@dataclass
class User:
    id: uuid.UUID
    phone_number: str
    timezone: str
    last_inbound_at: datetime | None = None
    daily_message_count: int = 0
    daily_count_reset_at: datetime | None = None
    pending_destructive_action: str | None = None
    pending_destructive_expires_at: datetime | None = None


@dataclass
class Tag:
    id: uuid.UUID
    user_id: uuid.UUID
    name: str


@dataclass
class Note:
    id: uuid.UUID
    user_id: uuid.UUID
    content: str
    occurred_at: datetime
    raw_message: str | None = None
    confidence: float | None = None
    tags: list[Tag] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass
class Habit:
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    aliases: list[str] = field(default_factory=list)
    active: bool = True


@dataclass
class HabitLog:
    id: uuid.UUID
    habit_id: uuid.UUID
    user_id: uuid.UUID
    occurred_at: datetime
    details: str | None = None


@dataclass
class Reminder:
    id: uuid.UUID
    user_id: uuid.UUID
    content: str
    scheduled_for: datetime
    status: ReminderStatus = "pending"
    sent_at: datetime | None = None
