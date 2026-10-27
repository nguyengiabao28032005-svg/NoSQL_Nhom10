import os
from typing import AsyncGenerator
import redis.asyncio as aioredis
import redis

# Đọc cấu hình kết nối Redis từ biến môi trường
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Connection pools
async_pool = aioredis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    max_connections=200
)

sync_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    max_connections=200
)

def get_sync_redis() -> redis.Redis:
    """Trả về Redis client đồng bộ (dùng cho scripts và sync helper)"""
    return redis.Redis(connection_pool=sync_pool)

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Dependency injection cho FastAPI: cung cấp async Redis client"""
    client = aioredis.Redis(connection_pool=async_pool)
    try:
        yield client
    finally:
        await client.aclose()

async def check_redis_connection() -> bool:
    """Kiểm tra PING tới Redis khi khởi động ứng dụng"""
    try:
        client = aioredis.Redis(connection_pool=async_pool)
        pong = await client.ping()
        await client.aclose()
        return bool(pong)
    except Exception as e:
        print(f"[ERROR] Không thể kết nối Redis: {e}")
        return False

def safe_delete_by_pattern(pattern: str, client: redis.Redis = None) -> int:
    """
    Xóa an toàn các key theo mẫu (pattern) dùng SCAN, 
    KHÔNG dùng FLUSHALL/FLUSHDB để bảo toàn dữ liệu hệ thống khác.
    """
    r = client or get_sync_redis()
    cursor = 0
    deleted_count = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            deleted_count += r.delete(*keys)
        if cursor == 0:
            break
    return deleted_count
