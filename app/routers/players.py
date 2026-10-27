from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
import redis.asyncio as aioredis
from app.db import get_redis
from app.schemas import PlayerCreate, PlayerUpdate, PlayerResponse

router = APIRouter(prefix="/players", tags=["Players - Quản lý người chơi"])

@router.post("", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(payload: PlayerCreate, r: aioredis.Redis = Depends(get_redis)):
    """
    Tạo người chơi mới:
    - Kiểm tra username trùng lặp qua key String `player:name:{username}`
    - Sinh ID tự tăng qua `INCR seq:player`
    - Lưu thông tin vào Hash `player:{id}`
    - Thêm id vào Set `players:all`
    - Khởi tạo điểm 0 trong Sorted Set `leaderboard:global`
    """
    # 1. Kiểm tra username đã tồn tại chưa
    name_key = f"player:name:{payload.username}"
    existing_id = await r.get(name_key)
    if existing_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên đăng nhập '{payload.username}' đã tồn tại trong hệ thống."
        )

    # 2. Sinh ID tự tăng (Lệnh Redis: INCR)
    player_id = await r.incr("seq:player")

    # 3. Chuẩn bị dữ liệu Hash
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    player_data = {
        "id": str(player_id),
        "username": payload.username,
        "display_name": payload.display_name,
        "email": payload.email,
        "avatar": payload.avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={player_id}",
        "created_at": now_str,
        "total_games": "0"
    }

    # 4. Thực thi transaction pipeline (MULTI/EXEC)
    async with r.pipeline(transaction=True) as pipe:
        pipe.set(name_key, player_id)
        pipe.hset(f"player:{player_id}", mapping=player_data)
        pipe.sadd("players:all", player_id)
        # Khởi tạo điểm 0 trong BXH toàn cục (Lệnh: ZADD)
        pipe.zadd("leaderboard:global", {f"player:{player_id}": 0}, nx=True)
        await pipe.execute()

    return PlayerResponse(
        id=player_id,
        username=player_data["username"],
        display_name=player_data["display_name"],
        email=player_data["email"],
        avatar=player_data["avatar"],
        created_at=player_data["created_at"],
        total_games=0
    )

@router.get("", response_model=List[PlayerResponse])
async def list_players(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Tìm theo username hoặc display_name"),
    order: Optional[str] = Query("asc", description="Thứ tự: 'asc' (tăng dần 1-151) hoặc 'desc'"),
    r: aioredis.Redis = Depends(get_redis)
):
    """
    Lấy danh sách người chơi có phân trang và tìm kiếm:
    - Đọc tập hợp ID từ Set `players:all` (Lệnh: SMEMBERS)
    - Mặc định sắp xếp ID tăng dần từ 1 đến hết
    - Pipeline lấy chi tiết Hash `player:{id}` (Lệnh: HGETALL)
    """
    all_ids = await r.smembers("players:all")
    if not all_ids:
        return []

    # Sắp xếp ID số nguyên tăng dần (1, 2, ..., 151)
    is_reverse = (order.lower() == "desc") if order else False
    sorted_ids = sorted([int(pid) for pid in all_ids], reverse=is_reverse)

    # Nếu có tìm kiếm, quét tìm kiếm trước khi phân trang
    players_list = []
    async with r.pipeline(transaction=False) as pipe:
        for pid in sorted_ids:
            pipe.hgetall(f"player:{pid}")
        results = await pipe.execute()

    for p in results:
        if not p or "id" not in p:
            continue
        if search:
            q = search.lower()
            if q not in p.get("username", "").lower() and q not in p.get("display_name", "").lower():
                continue
        players_list.append(PlayerResponse(
            id=int(p["id"]),
            username=p.get("username", ""),
            display_name=p.get("display_name", ""),
            email=p.get("email", ""),
            avatar=p.get("avatar", ""),
            created_at=p.get("created_at", ""),
            total_games=int(p.get("total_games", 0))
        ))

    return players_list[skip : skip + limit]

@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(player_id: int, r: aioredis.Redis = Depends(get_redis)):
    """Lấy chi tiết một người chơi theo ID (Lệnh: HGETALL)"""
    data = await r.hgetall(f"player:{player_id}")
    if not data or "id" not in data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người chơi với ID {player_id}."
        )
    return PlayerResponse(
        id=int(data["id"]),
        username=data.get("username", ""),
        display_name=data.get("display_name", ""),
        email=data.get("email", ""),
        avatar=data.get("avatar", ""),
        created_at=data.get("created_at", ""),
        total_games=int(data.get("total_games", 0))
    )

@router.put("/{player_id}", response_model=PlayerResponse)
async def update_player(player_id: int, payload: PlayerUpdate, r: aioredis.Redis = Depends(get_redis)):
    """
    Cập nhật thông tin người chơi:
    - Nếu thay đổi username, kiểm tra trùng và cập nhật lại key ánh xạ `player:name:{username}`
    - Cập nhật Hash `player:{id}` (Lệnh: HSET)
    """
    key = f"player:{player_id}"
    current = await r.hgetall(key)
    if not current or "id" not in current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người chơi với ID {player_id}."
        )

    current_username = current.get("username", "")
    new_username = payload.username

    # Xử lý đổi username nếu có
    if new_username and new_username != current_username:
        new_name_key = f"player:name:{new_username}"
        exists = await r.get(new_name_key)
        if exists and int(exists) != player_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tên đăng nhập '{new_username}' đã được sử dụng."
            )

    updates = {}
    if payload.display_name is not None:
        updates["display_name"] = payload.display_name
    if payload.email is not None:
        updates["email"] = payload.email
    if payload.avatar is not None:
        updates["avatar"] = payload.avatar
    if new_username and new_username != current_username:
        updates["username"] = new_username

    if updates:
        async with r.pipeline(transaction=True) as pipe:
            if new_username and new_username != current_username:
                pipe.delete(f"player:name:{current_username}")
                pipe.set(f"player:name:{new_username}", player_id)
            pipe.hset(key, mapping=updates)
            await pipe.execute()

    # Lấy lại thông tin mới nhất
    updated = await r.hgetall(key)
    return PlayerResponse(
        id=int(updated["id"]),
        username=updated.get("username", ""),
        display_name=updated.get("display_name", ""),
        email=updated.get("email", ""),
        avatar=updated.get("avatar", ""),
        created_at=updated.get("created_at", ""),
        total_games=int(updated.get("total_games", 0))
    )

@router.delete("/{player_id}", status_code=status.HTTP_200_OK)
async def delete_player(player_id: int, r: aioredis.Redis = Depends(get_redis)):
    """
    Xóa người chơi hoàn toàn:
    - Xóa Hash `player:{id}`
    - Xóa key ánh xạ `player:name:{username}`
    - SREM khỏi `players:all`
    - ZREM khỏi `leaderboard:global` và mọi `leaderboard:game:*`
    """
    key = f"player:{player_id}"
    current = await r.hgetall(key)
    if not current or "id" not in current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người chơi với ID {player_id}."
        )

    username = current.get("username", "")
    member = f"player:{player_id}"

    # Tìm mọi game leaderboard để xóa
    cursor = 0
    game_lb_keys = []
    while True:
        cursor, keys = await r.scan(cursor=cursor, match="leaderboard:game:*", count=100)
        game_lb_keys.extend(keys)
        if cursor == 0:
            break

    async with r.pipeline(transaction=True) as pipe:
        pipe.delete(key)
        if username:
            pipe.delete(f"player:name:{username}")
        pipe.srem("players:all", player_id)
        # ZREM khỏi global leaderboard
        pipe.zrem("leaderboard:global", member)
        # ZREM khỏi các game leaderboards
        for glb in game_lb_keys:
            pipe.zrem(glb, member)
        await pipe.execute()

    return {"message": f"Đã xóa thành công người chơi ID {player_id}."}
