from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
import redis.asyncio as aioredis
from app.db import get_redis
from app.schemas import LeaderboardEntry, AroundMeResponse

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard - Bảng xếp hạng"])

async def _build_leaderboard_entries(raw_items, r: aioredis.Redis, start_rank: int = 1) -> List[LeaderboardEntry]:
    """Helper chuyển đổi kết quả ZREVRANGE WITHSCORES thành danh sách LeaderboardEntry kèm profile"""
    if not raw_items:
        return []

    # raw_items dạng: [(b'player:1', 1500.0), ...] hoặc [( 'player:1', 1500.0), ...]
    entries = []
    pids = []
    scores = []
    for item in raw_items:
        member, score = item[0], item[1]
        if isinstance(member, bytes):
            member = member.decode("utf-8")
        # Tách player_id từ 'player:{id}'
        try:
            pid = int(member.split(":")[1])
        except Exception:
            continue
        pids.append(pid)
        scores.append(int(score))

    # Pipeline lấy thông tin định danh người chơi
    async with r.pipeline(transaction=False) as pipe:
        for pid in pids:
            pipe.hgetall(f"player:{pid}")
        profiles = await pipe.execute()

    for idx, (pid, score, profile) in enumerate(zip(pids, scores, profiles)):
        has_hash = bool(profile and "id" in profile)
        username = profile.get("username", f"player_{pid}") if has_hash else f"player:{pid}"
        display_name = profile.get("display_name", username) if (has_hash and profile.get("display_name")) else f"player:{pid}"
        avatar = profile.get("avatar", f"https://api.dicebear.com/7.x/bottts/svg?seed={pid}") if has_hash else f"https://api.dicebear.com/7.x/bottts/svg?seed={pid}"
        
        entries.append(LeaderboardEntry(
            rank=start_rank + idx,
            player_id=pid,
            username=username,
            display_name=display_name,
            avatar=avatar,
            score=score
        ))

    return entries

@router.get("/global", response_model=List[LeaderboardEntry])
async def get_global_leaderboard(
    top: int = Query(10, ge=1, le=100, description="Số lượng người chơi dẫn đầu"),
    r: aioredis.Redis = Depends(get_redis)
):
    """
    Lấy Top N Bảng xếp hạng toàn cục:
    - Sử dụng lệnh Redis: `ZREVRANGE leaderboard:global 0 {top-1} WITHSCORES`
    - Độ phức tạp: O(log(N) + M)
    """
    raw_top = await r.zrevrange("leaderboard:global", 0, top - 1, withscores=True)
    return await _build_leaderboard_entries(raw_top, r, start_rank=1)

@router.get("/game/{gid}", response_model=List[LeaderboardEntry])
async def get_game_leaderboard(
    gid: int,
    top: int = Query(10, ge=1, le=100, description="Số lượng người chơi dẫn đầu"),
    r: aioredis.Redis = Depends(get_redis)
):
    """
    Lấy Top N Bảng xếp hạng của một lượt chơi:
    - Sử dụng lệnh Redis: `ZREVRANGE leaderboard:game:{gid} 0 {top-1} WITHSCORES`
    """
    key = f"leaderboard:game:{gid}"
    raw_top = await r.zrevrange(key, 0, top - 1, withscores=True)
    return await _build_leaderboard_entries(raw_top, r, start_rank=1)

@router.get("/game/{gid}/player/{pid}")
async def get_player_rank_in_game(gid: int, pid: int, r: aioredis.Redis = Depends(get_redis)):
    """
    Lấy thứ hạng và điểm số của người chơi trong game:
    - Sử dụng lệnh: `ZREVRANK`, `ZSCORE`, `ZCARD`
    - Hạng thực tế hiển thị = ZREVRANK + 1 (vì Redis index từ 0)
    """
    key = f"leaderboard:game:{gid}"
    member = f"player:{pid}"

    async with r.pipeline(transaction=False) as pipe:
        pipe.zrevrank(key, member)
        pipe.zscore(key, member)
        pipe.zcard(key)
        rank_idx, score, total = await pipe.execute()

    if rank_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Người chơi {pid} chưa có điểm hoặc chưa tham gia game {gid}."
        )

    return {
        "game_id": gid,
        "player_id": pid,
        "rank": rank_idx + 1,
        "score": int(score) if score is not None else 0,
        "total_players": total
    }

@router.get("/game/{gid}/around/{pid}", response_model=AroundMeResponse)
async def get_around_me_in_game(gid: int, pid: int, r: aioredis.Redis = Depends(get_redis)):
    """
    Tính năng 'Xung quanh tôi' trong game (2 người trên và 2 người dưới):
    - Dùng `ZREVRANK` lấy vị trí R
    - Lấy dải [max(0, R - 2), R + 2] bằng `ZREVRANGE ... WITHSCORES`
    """
    key = f"leaderboard:game:{gid}"
    member = f"player:{pid}"

    rank_idx = await r.zrevrank(key, member)
    if rank_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Người chơi {pid} không có trong bảng xếp hạng game {gid}."
        )

    score = await r.zscore(key, member)
    total = await r.zcard(key)

    start_idx = max(0, rank_idx - 2)
    end_idx = rank_idx + 2

    raw_items = await r.zrevrange(key, start_idx, end_idx, withscores=True)
    entries = await _build_leaderboard_entries(raw_items, r, start_rank=start_idx + 1)

    return AroundMeResponse(
        player_rank=rank_idx + 1,
        player_score=int(score) if score is not None else 0,
        total_players=total,
        entries=entries
    )

@router.get("/global/player/{pid}")
async def get_player_rank_global(pid: int, r: aioredis.Redis = Depends(get_redis)):
    """Lấy thứ hạng và điểm số của người chơi trên BXH toàn cục (ZREVRANK, ZSCORE, ZCARD)"""
    key = "leaderboard:global"
    member = f"player:{pid}"

    async with r.pipeline(transaction=False) as pipe:
        pipe.zrevrank(key, member)
        pipe.zscore(key, member)
        pipe.zcard(key)
        rank_idx, score, total = await pipe.execute()

    if rank_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Người chơi {pid} chưa có trong bảng xếp hạng toàn cục."
        )

    return {
        "player_id": pid,
        "rank": rank_idx + 1,
        "score": int(score) if score is not None else 0,
        "total_players": total
    }

@router.get("/global/around/{pid}", response_model=AroundMeResponse)
async def get_around_me_global(pid: int, r: aioredis.Redis = Depends(get_redis)):
    """Tính năng 'Xung quanh tôi' trên BXH toàn cục"""
    key = "leaderboard:global"
    member = f"player:{pid}"

    rank_idx = await r.zrevrank(key, member)
    if rank_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Người chơi {pid} không có trong bảng xếp hạng toàn cục."
        )

    score = await r.zscore(key, member)
    total = await r.zcard(key)

    start_idx = max(0, rank_idx - 2)
    end_idx = rank_idx + 2

    raw_items = await r.zrevrange(key, start_idx, end_idx, withscores=True)
    entries = await _build_leaderboard_entries(raw_items, r, start_rank=start_idx + 1)

    return AroundMeResponse(
        player_rank=rank_idx + 1,
        player_score=int(score) if score is not None else 0,
        total_players=total,
        entries=entries
    )
