import json
import redis.asyncio as aioredis
from app.config import settings


class RedisEventBus:
    def __init__(self):
        pass

    def _get_redis(self):
        return aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    def _channel_name(self, blog_id: str) -> str:
        return f"blog:{blog_id}:events"

    async def publish(self, blog_id: str, event: dict):
        r = self._get_redis()
        try:
            channel = self._channel_name(blog_id)
            await r.publish(channel, json.dumps(event, default=str))
        finally:
            await r.close()

    async def subscribe(self, blog_id: str):
        r = self._get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(self._channel_name(blog_id))
        return pubsub

    async def unsubscribe(self, pubsub):
        await pubsub.unsubscribe()
        await pubsub.close()


event_bus = RedisEventBus()
