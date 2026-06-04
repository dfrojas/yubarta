import os
from redis.asyncio import Redis


redis = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True
)

async def idempotency_check(event_id: str) -> bool:
    return await redis.set(f"evt:{event_id}", "1", nx=True, ex=24*3600) is True


async def bump_batch_alarms(fingerprint: str, window_sec: int) -> int:
    key = f"dedupe:{fingerprint}"
    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, window_sec, nx=True)
    count, _ = await pipe.execute()
    return int(count)
