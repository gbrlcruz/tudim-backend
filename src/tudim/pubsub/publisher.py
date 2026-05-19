import json
import logging
from google.cloud import pubsub_v1
from pydantic import BaseModel

from tudim.config import settings

log = logging.getLogger("tudim.pubsub")

_publisher = pubsub_v1.PublisherClient()
_topic_path = _publisher.topic_path(settings.gcp_project, "tudim-incoming-messages")


class IncomingMessageEvent(BaseModel):
    message_sid: str
    from_e164: str
    body: str
    num_media: int
    received_at: float


async def publish_incoming(ev: IncomingMessageEvent) -> str:
    data = ev.model_dump_json().encode("utf-8")
    future = _publisher.publish(_topic_path, data=data, message_sid=ev.message_sid)
    return future.result(timeout=5)