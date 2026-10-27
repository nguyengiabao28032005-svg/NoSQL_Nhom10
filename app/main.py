import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.db import check_redis_connection
from app.routers import players, questions, games, leaderboard, stream, admin_api
from app.routers.stream import keyspace_listener_task

keyspace_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global keyspace_task
    # Khởi động: Kiểm tra kết nối Redis PING
    connected = await check_redis_connection()
    if not connected:
        print("[CRITICAL] Không thể kết nối tới Redis! Vui lòng kiểm tra Docker container 'redis'.")
    else:
        print("[INIT] Kết nối Redis thành công (PONG). Sẵn sàng phục vụ.")

    # Khởi chạy background task lắng nghe Keyspace Notifications
    keyspace_task = asyncio.create_task(keyspace_listener_task())

    yield

    # Tắt ứng dụng: Hủy task background
    if keyspace_task:
        keyspace_task.cancel()
        try:
            await keyspace_task
        except asyncio.CancelledError:
            pass
    print("[SHUTDOWN] Đã dừng toàn bộ dịch vụ an toàn.")

app = FastAPI(
    title="Hệ thống Bảng Xếp Hạng Thời Gian Thực (Real-Time Leaderboard)",
    description="Đồ án CSDL NoSQL - Đề tài 05. Sử dụng Redis Key-Value & Sorted Sets (ZSET) với SSE và Pub/Sub.",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS để thuận tiện kiểm thử
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Đăng ký các router nghiệp vụ
app.include_router(players.router)
app.include_router(questions.router)
app.include_router(games.router)
app.include_router(leaderboard.router)
app.include_router(stream.router)
app.include_router(admin_api.router)

# Mount thư mục static phục vụ giao diện người dùng
import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    """Chuyển hướng trang chủ vào giao diện thi đấu"""
    return RedirectResponse(url="/static/index.html")

@app.get("/health", tags=["Hệ thống"])
async def health_check():
    """Kiểm tra sức khỏe hệ thống và kết nối Redis"""
    is_ok = await check_redis_connection()
    return {
        "status": "healthy" if is_ok else "unhealthy",
        "redis_connected": is_ok,
        "service": "Real-Time Leaderboard API"
    }
