from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
import json
import redis.asyncio as aioredis
from app.db import get_redis
from app.schemas import (
    GameCreate, GameStatusUpdate, GameResponse, 
    QuestionInGame, AnswerSubmit, AnswerResult
)

router = APIRouter(prefix="/games", tags=["Games - Quản lý lượt thi đấu"])

@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(payload: GameCreate, r: aioredis.Redis = Depends(get_redis)):
    """
    Tạo lượt thi đấu mới:
    - Sinh ID tự tăng: `INCR seq:game`
    - Lưu Hash `game:{gid}` với trạng thái ban đầu 'waiting'
    - Chọn ngẫu nhiên câu hỏi qua `SRANDMEMBER` lưu vào List `game:{gid}:questions`
    """
    gid = await r.incr("seq:game")

    # Chọn câu hỏi theo category hoặc toàn bộ
    if payload.category:
        source_set = f"questions:cat:{payload.category.strip()}"
    else:
        source_set = "questions:all"

    q_count = payload.question_count
    # Lấy ngẫu nhiên danh sách câu hỏi không trùng (Lệnh: SRANDMEMBER)
    selected_qids = await r.srandmember(source_set, q_count)
    if not selected_qids:
        # Nếu chưa có câu hỏi nào thì fallback sang questions:all
        selected_qids = await r.srandmember("questions:all", q_count)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    game_data = {
        "id": str(gid),
        "name": payload.name,
        "status": "waiting",
        "created_at": now_str,
        "question_count": str(len(selected_qids) if selected_qids else 0)
    }

    async with r.pipeline(transaction=True) as pipe:
        pipe.hset(f"game:{gid}", mapping=game_data)
        # Lưu thứ tự câu hỏi vào List (Lệnh: RPUSH)
        if selected_qids:
            pipe.rpush(f"game:{gid}:questions", *[str(q) for q in selected_qids])
        await pipe.execute()

    return GameResponse(
        id=gid,
        name=game_data["name"],
        status=game_data["status"],
        created_at=game_data["created_at"],
        question_count=int(game_data["question_count"]),
        players_count=0
    )

@router.get("", response_model=List[GameResponse])
async def list_games(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    r: aioredis.Redis = Depends(get_redis)
):
    """Lấy danh sách các lượt thi đấu kèm số lượng người tham gia"""
    cursor = 0
    game_keys = []
    while True:
        cursor, keys = await r.scan(cursor=cursor, match="game:[0-9]*", count=100)
        # Chỉ lấy các key dạng game:{gid} (không lấy game:{gid}:questions hay game:{gid}:players)
        for k in keys:
            parts = k.split(":")
            if len(parts) == 2 and parts[1].isdigit():
                game_keys.append(k)
        if cursor == 0:
            break

    if not game_keys:
        return []

    # Sắp xếp theo ID giảm dần (game mới nhất lên đầu)
    game_keys.sort(key=lambda k: int(k.split(":")[1]), reverse=True)
    paged_keys = game_keys[skip : skip + limit]

    games = []
    async with r.pipeline(transaction=False) as pipe:
        for k in paged_keys:
            pipe.hgetall(k)
            gid = k.split(":")[1]
            pipe.scard(f"game:{gid}:players")
        results = await pipe.execute()

    for i in range(0, len(results), 2):
        gdata = results[i]
        p_count = results[i + 1] if i + 1 < len(results) else 0
        if not gdata or "id" not in gdata:
            continue
        games.append(GameResponse(
            id=int(gdata["id"]),
            name=gdata.get("name", ""),
            status=gdata.get("status", "waiting"),
            created_at=gdata.get("created_at", ""),
            question_count=int(gdata.get("question_count", 0)),
            players_count=int(p_count)
        ))

    return games

@router.get("/{gid}", response_model=GameResponse)
async def get_game(gid: int, r: aioredis.Redis = Depends(get_redis)):
    """Lấy thông tin chi tiết một lượt chơi (Lệnh: HGETALL + SCARD)"""
    data = await r.hgetall(f"game:{gid}")
    if not data or "id" not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy game ID {gid}.")
    
    players_count = await r.scard(f"game:{gid}:players")
    return GameResponse(
        id=int(data["id"]),
        name=data.get("name", ""),
        status=data.get("status", "waiting"),
        created_at=data.get("created_at", ""),
        question_count=int(data.get("question_count", 0)),
        players_count=players_count
    )

@router.put("/{gid}/status", response_model=GameResponse)
@router.patch("/{gid}/status", response_model=GameResponse)
async def update_game_status(gid: int, payload: GameStatusUpdate, r: aioredis.Redis = Depends(get_redis)):
    """Đổi trạng thái game: 'waiting' -> 'running' -> 'finished'"""
    exists = await r.exists(f"game:{gid}")
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy game ID {gid}.")

    await r.hset(f"game:{gid}", "status", payload.status)
    
    # Broadcast thông báo đổi trạng thái game
    event_payload = json.dumps({
        "type": "game_status_changed",
        "game_id": gid,
        "status": payload.status
    })
    await r.publish(f"channel:game:{gid}", event_payload)

    return await get_game(gid, r)

@router.post("/{gid}/join", status_code=status.HTTP_200_OK)
async def join_game(gid: int, player_id: int = Query(...), r: aioredis.Redis = Depends(get_redis)):
    """
    Người chơi tham gia vào lượt thi đấu:
    - Kiểm tra game và người chơi tồn tại
    - SADD vào `game:{gid}:players`
    - Khởi tạo điểm 0 trong `leaderboard:game:{gid}` bằng ZADD NX
    - Tăng số lần chơi `total_games` của người chơi
    - Broadcast thông báo có người tham gia
    """
    game_data = await r.hgetall(f"game:{gid}")
    if not game_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Game ID {gid} không tồn tại.")

    p_data = await r.hgetall(f"player:{player_id}")
    if not p_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Người chơi ID {player_id} không tồn tại.")

    member = f"player:{player_id}"

    async with r.pipeline(transaction=True) as pipe:
        # Thêm người chơi vào Set người tham gia (Lệnh: SADD)
        pipe.sadd(f"game:{gid}:players", player_id)
        # Khởi tạo điểm 0 trong BXH của game nếu chưa có (Lệnh: ZADD NX)
        pipe.zadd(f"leaderboard:game:{gid}", {member: 0}, nx=True)
        # Tăng tổng số game đã tham gia
        pipe.hincrby(f"player:{player_id}", "total_games", 1)
        await pipe.execute()

    # Lấy thông tin điểm và hạng hiện tại
    rank = await r.zrevrank(f"leaderboard:game:{gid}", member)
    score = await r.zscore(f"leaderboard:game:{gid}", member)

    # Broadcast event join game
    event_payload = json.dumps({
        "type": "player_joined",
        "game_id": gid,
        "player_id": player_id,
        "username": p_data.get("username", ""),
        "display_name": p_data.get("display_name", ""),
        "avatar": p_data.get("avatar", ""),
        "score": int(score) if score is not None else 0,
        "rank": (rank + 1) if rank is not None else 1
    })
    await r.publish(f"channel:game:{gid}", event_payload)

    return {
        "message": f"Người chơi {player_id} đã tham gia game {gid} thành công.",
        "game_id": gid,
        "player_id": player_id,
        "score": int(score) if score is not None else 0,
        "rank": (rank + 1) if rank is not None else 1
    }

@router.get("/{gid}/questions", response_model=List[QuestionInGame])
async def get_game_questions(gid: int, r: aioredis.Redis = Depends(get_redis)):
    """
    Lấy danh sách câu hỏi của lượt chơi:
    - Đọc danh sách ID từ List `game:{gid}:questions` (Lệnh: LRANGE)
    - Trả về danh sách câu hỏi với schema `QuestionInGame` (TUYỆT ĐỐI KHÔNG CÓ TRƯỜNG correct)
    """
    exists = await r.exists(f"game:{gid}")
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Game ID {gid} không tồn tại.")

    # Đọc toàn bộ câu hỏi trong List (Lệnh: LRANGE)
    qids = await r.lrange(f"game:{gid}:questions", 0, -1)
    if not qids:
        return []

    questions = []
    async with r.pipeline(transaction=False) as pipe:
        for qid in qids:
            pipe.hgetall(f"question:{qid}")
        results = await pipe.execute()

    for q in results:
        if not q or "id" not in q:
            continue
        # Trả về QuestionInGame: không có trường correct
        questions.append(QuestionInGame(
            id=int(q["id"]),
            content=q.get("content", ""),
            A=q.get("A", ""),
            B=q.get("B", ""),
            C=q.get("C", ""),
            D=q.get("D", ""),
            category=q.get("category", "Chung"),
            points=int(q.get("points", 100))
        ))

    return questions

@router.post("/{gid}/answer", response_model=AnswerResult, status_code=status.HTTP_200_OK)
async def submit_answer(gid: int, payload: AnswerSubmit, r: aioredis.Redis = Depends(get_redis)):
    """
    Nộp câu trả lời và chấm điểm (Barem 2.5đ):
    - Kiểm tra game tồn tại (404)
    - Kiểm tra trạng thái game phải là 'running' (400)
    - Kiểm tra người chơi đã tham gia game (400)
    - Kiểm tra câu hỏi thuộc danh sách đề thi của game (400)
    - Kiểm tra chống trả lời 2 lần qua Set `game:{gid}:answered:{pid}` (400)
    - Nếu đúng: Dùng pipeline giao dịch ZINCRBY cho cả BXH game và BXH toàn cục
    - Lấy thứ hạng tức thì qua ZREVRANK (hạng = index + 1)
    - Broadcast thông điệp đổi hạng qua `PUBLISH channel:game:{gid}`
    """
    # 1. Kiểm tra game tồn tại (404)
    game_data = await r.hgetall(f"game:{gid}")
    if not game_data or "id" not in game_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lượt thi đấu ID {gid} không tồn tại."
        )

    # 2. Kiểm tra trạng thái game phải là 'running' (400)
    if game_data.get("status") != "running":
        if game_data.get("status") == "finished":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trận đấu đã kết thúc! Người chơi không được phép trả lời nữa."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trận đấu chưa bắt đầu! Vui lòng chờ quản trị viên kích hoạt."
            )

    pid = payload.player_id
    qid = payload.question_id

    # 3. Kiểm tra người chơi đã join game chưa (400)
    is_joined = await r.sismember(f"game:{gid}:players", pid)
    if not is_joined:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Người chơi {pid} chưa tham gia lượt thi đấu này."
        )

    # 4. Kiểm tra câu hỏi có thuộc game hay không (chống hack câu hỏi ngoài đề)
    game_qids = await r.lrange(f"game:{gid}:questions", 0, -1)
    if str(qid) not in game_qids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Câu hỏi {qid} không thuộc lượt thi đấu này."
        )

    # 5. Kiểm tra chống trả lời 2 lần: Dùng SADD vào Set answered
    # SADD trả về 1 nếu phần tử mới được thêm, 0 nếu đã tồn tại từ trước
    added = await r.sadd(f"game:{gid}:answered:{pid}", qid)
    if added == 0:
        # Lấy số thứ tự hiển thị của câu hỏi trong lượt thi đấu (1-based)
        q_order = (game_qids.index(str(qid)) + 1) if str(qid) in game_qids else qid
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Câu hỏi số {q_order} đã được bạn trả lời trước đó! Không thể tính điểm hai lần."
        )

    # 6. Lấy dữ liệu câu hỏi và so khớp đáp án đúng
    q_data = await r.hgetall(f"question:{qid}")
    if not q_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy dữ liệu cho câu hỏi {qid}."
        )

    correct_choice = q_data.get("correct", "").strip().upper()
    user_choice = payload.choice.strip().upper()
    is_correct = (user_choice == correct_choice)

    points_to_award = int(q_data.get("points", 100)) if is_correct else 0
    member = f"player:{pid}"

    # 7. Lưu đáp án đã chọn và cập nhật điểm số nguyên tử
    async with r.pipeline(transaction=True) as pipe:
        # Lưu lựa chọn của thí sinh và kết quả vào Hash
        pipe.hset(f"game:{gid}:answers:{pid}", str(qid), user_choice)
        pipe.hset(f"game:{gid}:results:{pid}", str(qid), "1" if is_correct else "0")
        if is_correct:
            # Lệnh: ZINCRBY tăng điểm cho BXH trận đấu
            pipe.zincrby(f"leaderboard:game:{gid}", points_to_award, member)
            # Lệnh: ZINCRBY tăng điểm cho BXH toàn cục
            pipe.zincrby("leaderboard:global", points_to_award, member)
        await pipe.execute()

    # 8. Lấy điểm số và thứ hạng hiện tại tức thì
    async with r.pipeline(transaction=False) as pipe:
        pipe.zscore(f"leaderboard:game:{gid}", member)
        pipe.zrevrank(f"leaderboard:game:{gid}", member)
        current_score, rank_idx = await pipe.execute()

    new_score = int(current_score) if current_score is not None else 0
    # Hạng hiển thị = ZREVRANK + 1 (vì index Redis tính từ 0)
    new_rank = (rank_idx + 1) if rank_idx is not None else 1

    # 9. Nếu đúng: Broadcast thông báo đổi hạng qua Redis Pub/Sub
    if is_correct:
        p_data = await r.hgetall(f"player:{pid}")
        event_payload = json.dumps({
            "type": "rank_updated",
            "game_id": gid,
            "player_id": pid,
            "username": p_data.get("username", f"player_{pid}"),
            "display_name": p_data.get("display_name", f"Player {pid}"),
            "avatar": p_data.get("avatar", ""),
            "points_earned": points_to_award,
            "new_score": new_score,
            "new_rank": new_rank
        })
        await r.publish(f"channel:game:{gid}", event_payload)

    return AnswerResult(
        correct=is_correct,
        points_earned=points_to_award,
        new_score=new_score,
        new_rank=new_rank,
        message="Chính xác! Bạn đã nhận được điểm thưởng." if is_correct else "Rất tiếc! Đáp án chưa chính xác."
    )

@router.get("/{gid}/answers/{pid}")
async def get_player_answers(gid: int, pid: int, r: aioredis.Redis = Depends(get_redis)):
    """Lấy danh sách các câu hỏi đã trả lời và phương án đã chọn của thí sinh trong trận đấu"""
    answered_qids = await r.smembers(f"game:{gid}:answered:{pid}")
    answers = await r.hgetall(f"game:{gid}:answers:{pid}")
    results = await r.hgetall(f"game:{gid}:results:{pid}")
    data = {}
    for qid_str in answered_qids:
        choice = answers.get(qid_str, "")
        data[qid_str] = {
            "choice": choice,
            "correct": results.get(qid_str) == "1"
        }
    return data

