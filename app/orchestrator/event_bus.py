import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, blog_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers[blog_id].append(queue)
        return queue

    def unsubscribe(self, blog_id: str, queue: asyncio.Queue):
        if blog_id in self._subscribers:
            self._subscribers[blog_id].remove(queue)
            if not self._subscribers[blog_id]:
                del self._subscribers[blog_id]

    async def publish(self, blog_id: str, event: dict):
        for queue in self._subscribers.get(blog_id, []):
            await queue.put(event)


event_bus = EventBus()
