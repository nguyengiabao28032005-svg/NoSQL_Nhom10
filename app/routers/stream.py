import asyncio
import json
import time
from typing import Set
from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
from app.db import async_pool
from app.routers.leaderboard import get_game_leaderboard, get_global_leaderboard

router = APIRouter(tags=["Stream - Real-time SSE"])

# Tập hợp theo dõi các game_id đang có client kết nối SSE để hỗ trợ broadcast
active_game_streams: Set[int] = set()

# Quản lý debounce 150ms cho keyspace notifications
_last_publish_time = {}

async def publish_debounced_change(redis_client: aioredis.Redis, channel: str, message: dict, debounce_ms: int = 150):
    """Debounce 150ms tránh bắn trùng lặp giữa API PUBLISH thủ công và Keyspace notification"""
    now = time.time() * 1000  # ms
    last = _last_publish_time.get(channel, 0)
    if now - last < debounce_ms:
        return
    _last_publish_time[channel] = now
    await redis_client.publish(channel, json.dumps(message))

async def keyspace_listener_task():
    """
    Background Task: Lắng nghe Redis Keyspace Notifications
    - Bật cờ 'Ez' (Keyevent trên ZSET)
    - Subscribe 2 kênh: __keyevent@0__:zincrby và __keyevent@0__:zadd
    - Tự động phát hiện khi admin/giảng viên gõ ZINCRBY trực tiếp từ redis-cli
    """
    client = aioredis.Redis(connection_pool=async_pool)
    try:
        # Bật keyspace notifications cho Redis (cờ Ez theo đúng yêu cầu)
        try:
            await client.config_set("notify-keyspace-events", "Ez")
            print("[KEYSPACE] Đã kích hoạt notify-keyspace-events = Ez thành công.")
        except Exception as ce:
            print(f"[KEYSPACE WARNING] Không thể cấu hình config_set: {ce}")

        pubsub = client.pubsub()
        await pubsub.psubscribe("__keyevent@*__:zincr*", "__keyevent@*__:zadd*")
        print("[KEYSPACE] Đang lắng nghe kênh __keyevent@*__:zincr* và __keyevent@*__:zadd*...")

        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue

            key_name = message.get("data")
            if isinstance(key_name, bytes):
                key_name = key_name.decode("utf-8")

            if not key_name:
                continue

            # Xử lý khi key đổi là leaderboard:game:{gid}
            if key_name.startswith("leaderboard:game:"):
                try:
                    gid = int(key_name.split(":")[2])
                    msg = {
                        "type": "leaderboard_changed",
                        "game_id": gid,
                        "source": "keyspace"
                    }
                    await publish_debounced_change(client, f"channel:game:{gid}", msg)
                except Exception as e:
                    pass

            # Xử lý khi key đổi là leaderboard:global
            elif key_name == "leaderboard:global":
                msg = {
                    "type": "global_leaderboard_changed",
                    "source": "keyspace"
                }
                # Broadcast đến toàn bộ các game stream đang mở
                for gid in list(active_game_streams):
                    await publish_debounced_change(client, f"channel:game:{gid}", msg)

    except asyncio.CancelledError:
        print("[KEYSPACE] Task keyspace listener đã dừng.")
    except Exception as e:
        print(f"[KEYSPACE ERROR] Lỗi trong keyspace listener: {e}")
    finally:
        await client.aclose()

@router.get("/stream/{gid}")
async def stream_game_events(gid: int, request: Request):
    """
    Server-Sent Events (SSE) cho lượt thi đấu {gid}:
    - Đẩy ngay Top 10 ban đầu khi client kết nối
    - Lắng nghe sự kiện từ kênh `channel:game:{gid}` (Pub/Sub)
    - Heartbeat định kỳ 15 giây
    - Tự động hủy đăng ký khi client đóng tab/ngắt kết nối
    """
    async def event_generator():
        client = aioredis.Redis(connection_pool=async_pool)
        pubsub = client.pubsub()
        channel_name = f"channel:game:{gid}"
        await pubsub.subscribe(channel_name)
        active_game_streams.add(gid)

        try:
            # 1. Gửi ngay dữ liệu BXH khởi tạo (Init data) để UI render tức thì
            initial_top = await get_game_leaderboard(gid=gid, top=10, r=client)
            initial_payload = {
                "type": "init_leaderboard",
                "game_id": gid,
                "top": [entry.model_dump() for entry in initial_top]
            }
            yield f"data: {json.dumps(initial_payload)}\n\n"

            # 2. Vòng lặp nhận event và gửi heartbeat 15 giây
            last_heartbeat = time.time()
            while True:
                # Kiểm tra client có bị ngắt kết nối không
                if await request.is_disconnected():
                    break

                # Đọc tin nhắn từ pubsub không khóa (timeout 1.0 giây)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    payload_data = message["data"]
                    if isinstance(payload_data, bytes):
                        payload_data = payload_data.decode("utf-8")
                    yield f"data: {payload_data}\n\n"

                # Heartbeat 15 giây giữ kết nối
                now = time.time()
                if now - last_heartbeat >= 15.0:
                    yield f"data: {json.dumps({'type': 'ping', 'timestamp': int(now)})}\n\n"
                    last_heartbeat = now

                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        finally:
            active_game_streams.discard(gid)
            await pubsub.unsubscribe(channel_name)
            await client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
