"""Poll event bus: Redis pub/sub when configured, in-memory fallback for local dev."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

_redis = None
_local_queues: dict[int, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
_local_lock = asyncio.Lock()


def _channel(poll_id: int) -> str:
    return f"poll:{poll_id}:events"


async def init_event_bus(redis_url: str | None) -> None:
    global _redis
    if not redis_url:
        logger.info("REDIS_URL not set — poll events use in-memory pub/sub (single worker only)")
        return
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url, decode_responses=True)
        await client.ping()
        _redis = client
        logger.info("Poll event bus connected to Redis")
    except Exception as exc:
        logger.warning("Redis unavailable (%s); using in-memory poll event bus", exc)
        _redis = None


async def close_event_bus() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def publish_poll_event(poll_id: int, event_type: str, **payload: Any) -> None:
    message: dict[str, Any] = {"type": event_type, "poll_id": poll_id, **payload}
    data = json.dumps(message, ensure_ascii=False)
    if _redis is not None:
        await _redis.publish(_channel(poll_id), data)
        return
    async with _local_lock:
        for q in list(_local_queues[poll_id]):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass


def schedule_poll_event(poll_id: int, event_type: str, **payload: Any) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(publish_poll_event(poll_id, event_type, **payload))


async def subscribe_poll_events(poll_id: int) -> AsyncIterator[dict[str, Any]]:
    if _redis is not None:
        pubsub = _redis.pubsub()
        await pubsub.subscribe(_channel(poll_id))
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                yield json.loads(raw["data"])
        finally:
            await pubsub.unsubscribe(_channel(poll_id))
            await pubsub.close()
        return

    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
    async with _local_lock:
        _local_queues[poll_id].append(q)
    try:
        while True:
            yield await q.get()
    finally:
        async with _local_lock:
            if q in _local_queues[poll_id]:
                _local_queues[poll_id].remove(q)
