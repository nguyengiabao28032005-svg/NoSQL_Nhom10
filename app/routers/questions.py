from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
import redis.asyncio as aioredis
from app.db import get_redis
from app.schemas import QuestionCreate, QuestionUpdate, QuestionResponse, CategoryCreate, CategoryDetail

router = APIRouter(prefix="/questions", tags=["Questions - Ngân hàng câu hỏi"])

@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(payload: QuestionCreate, r: aioredis.Redis = Depends(get_redis)):
    """
    Tạo câu hỏi mới:
    - Sinh ID tự tăng: `INCR seq:question`
    - Lưu dữ liệu vào Hash `question:{id}`
    - Thêm ID vào Set `questions:all`
    - Cập nhật chỉ mục chủ đề: `SADD questions:cat:{category} {id}`
    """
    qid = await r.incr("seq:question")
    cat = payload.category.strip() or "Chung"

    q_data = {
        "id": str(qid),
        "content": payload.content,
        "A": payload.A,
        "B": payload.B,
        "C": payload.C,
        "D": payload.D,
        "correct": payload.correct.upper(),
        "category": cat,
        "points": str(payload.points)
    }

    async with r.pipeline(transaction=True) as pipe:
        pipe.hset(f"question:{qid}", mapping=q_data)
        pipe.sadd("questions:all", qid)
        pipe.sadd(f"questions:cat:{cat}", qid)
        pipe.sadd("categories:all", cat)
        await pipe.execute()

    return QuestionResponse(
        id=qid,
        content=q_data["content"],
        A=q_data["A"],
        B=q_data["B"],
        C=q_data["C"],
        D=q_data["D"],
        correct=q_data["correct"],
        category=q_data["category"],
        points=int(q_data["points"])
    )

@router.get("", response_model=List[QuestionResponse])
async def list_questions(
    category: Optional[str] = Query(None, description="Lọc theo chủ đề"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    r: aioredis.Redis = Depends(get_redis)
):
    """
    Danh sách câu hỏi có phân trang và lọc theo category:
    - Nếu có category: đọc từ Set `questions:cat:{category}` (Lệnh: SMEMBERS)
    - Nếu không: đọc từ Set `questions:all` (Lệnh: SMEMBERS)
    - Pipeline lấy chi tiết Hash `question:{id}` (Lệnh: HGETALL)
    """
    if category:
        target_set = f"questions:cat:{category.strip()}"
    else:
        target_set = "questions:all"

    all_qids = await r.smembers(target_set)
    if not all_qids:
        return []

    sorted_ids = sorted([int(x) for x in all_qids])
    paged_ids = sorted_ids[skip : skip + limit]

    questions = []
    async with r.pipeline(transaction=False) as pipe:
        for qid in paged_ids:
            pipe.hgetall(f"question:{qid}")
        results = await pipe.execute()

    for q in results:
        if not q or "id" not in q:
            continue
        questions.append(QuestionResponse(
            id=int(q["id"]),
            content=q.get("content", ""),
            A=q.get("A", ""),
            B=q.get("B", ""),
            C=q.get("C", ""),
            D=q.get("D", ""),
            correct=q.get("correct", "A"),
            category=q.get("category", "Chung"),
            points=int(q.get("points", 100))
        ))

    return questions

@router.get("/categories", response_model=List[str])
async def list_categories(r: aioredis.Redis = Depends(get_redis)):
    """Lấy danh sách các chủ đề hiện có trong hệ thống (kết hợp Set categories:all và scan questions:cat:*)"""
    cursor = 0
    categories = set()

    # Đọc từ Set categories:all
    explicit_cats = await r.smembers("categories:all")
    for c in explicit_cats:
        if c:
            categories.add(c)

    # Quét thêm từ các key questions:cat:*
    while True:
        cursor, keys = await r.scan(cursor=cursor, match="questions:cat:*", count=100)
        for k in keys:
            cat_name = k.replace("questions:cat:", "")
            if cat_name:
                categories.add(cat_name)
        if cursor == 0:
            break

    # Đồng bộ ngược vào categories:all
    if categories:
        await r.sadd("categories:all", *categories)

    return sorted(list(categories))

@router.get("/categories/details", response_model=List[CategoryDetail])
async def list_categories_details(r: aioredis.Redis = Depends(get_redis)):
    """Lấy danh sách chi tiết các chủ đề kèm số lượng câu hỏi trong mỗi chủ đề"""
    cats = await list_categories(r)
    if not cats:
        return []

    async with r.pipeline(transaction=False) as pipe:
        for c in cats:
            pipe.scard(f"questions:cat:{c}")
        counts = await pipe.execute()

    return [CategoryDetail(name=c, count=cnt) for c, cnt in zip(cats, counts)]

@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, r: aioredis.Redis = Depends(get_redis)):
    """Tạo mới một chủ đề câu hỏi"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên chủ đề không được để trống.")
    exists = await r.sismember("categories:all", name)
    if exists:
        raise HTTPException(status_code=400, detail=f"Chủ đề '{name}' đã tồn tại trong hệ thống.")

    await r.sadd("categories:all", name)
    return {"name": name, "message": f"Đã thêm chủ đề '{name}' thành công."}

@router.delete("/categories/{name}", status_code=status.HTTP_200_OK)
async def delete_category(name: str, r: aioredis.Redis = Depends(get_redis)):
    """Xóa chủ đề (chỉ cho phép xóa khi không còn câu hỏi nào thuộc chủ đề này)"""
    name = name.strip()
    count = await r.scard(f"questions:cat:{name}")
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chủ đề '{name}' hiện đang có {count} câu hỏi! Vui lòng xóa hoặc chuyển chủ đề các câu hỏi này trước khi xóa."
        )

    await r.srem("categories:all", name)
    await r.delete(f"questions:cat:{name}")
    return {"message": f"Đã xóa chủ đề '{name}' thành công."}

@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int, r: aioredis.Redis = Depends(get_redis)):
    """Lấy chi tiết một câu hỏi theo ID (Lệnh: HGETALL)"""
    data = await r.hgetall(f"question:{question_id}")
    if not data or "id" not in data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy câu hỏi với ID {question_id}."
        )
    return QuestionResponse(
        id=int(data["id"]),
        content=data.get("content", ""),
        A=data.get("A", ""),
        B=data.get("B", ""),
        C=data.get("C", ""),
        D=data.get("D", ""),
        correct=data.get("correct", "A"),
        category=data.get("category", "Chung"),
        points=int(data.get("points", 100))
    )

@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: int, payload: QuestionUpdate, r: aioredis.Redis = Depends(get_redis)):
    """
    Cập nhật câu hỏi:
    - Nếu đổi category, cập nhật lại chỉ mục Set `questions:cat:*`
    - Cập nhật Hash `question:{id}`
    """
    key = f"question:{question_id}"
    current = await r.hgetall(key)
    if not current or "id" not in current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy câu hỏi với ID {question_id}."
        )

    old_cat = current.get("category", "Chung")
    new_cat = payload.category.strip() if payload.category else None

    updates = {}
    if payload.content is not None:
        updates["content"] = payload.content
    if payload.A is not None:
        updates["A"] = payload.A
    if payload.B is not None:
        updates["B"] = payload.B
    if payload.C is not None:
        updates["C"] = payload.C
    if payload.D is not None:
        updates["D"] = payload.D
    if payload.correct is not None:
        updates["correct"] = payload.correct.upper()
    if payload.points is not None:
        updates["points"] = str(payload.points)
    if new_cat and new_cat != old_cat:
        updates["category"] = new_cat

    if updates:
        async with r.pipeline(transaction=True) as pipe:
            if new_cat and new_cat != old_cat:
                pipe.srem(f"questions:cat:{old_cat}", question_id)
                pipe.sadd(f"questions:cat:{new_cat}", question_id)
            pipe.hset(key, mapping=updates)
            await pipe.execute()

    updated = await r.hgetall(key)
    return QuestionResponse(
        id=int(updated["id"]),
        content=updated.get("content", ""),
        A=updated.get("A", ""),
        B=updated.get("B", ""),
        C=updated.get("C", ""),
        D=updated.get("D", ""),
        correct=updated.get("correct", "A"),
        category=updated.get("category", "Chung"),
        points=int(updated.get("points", 100))
    )

@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
async def delete_question(question_id: int, r: aioredis.Redis = Depends(get_redis)):
    """
    Xóa câu hỏi:
    - Xóa Hash `question:{id}`
    - SREM khỏi `questions:all` và `questions:cat:{category}`
    """
    key = f"question:{question_id}"
    current = await r.hgetall(key)
    if not current or "id" not in current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy câu hỏi với ID {question_id}."
        )

    cat = current.get("category", "Chung")
    async with r.pipeline(transaction=True) as pipe:
        pipe.delete(key)
        pipe.srem("questions:all", question_id)
        pipe.srem(f"questions:cat:{cat}", question_id)
        await pipe.execute()

    return {"message": f"Đã xóa thành công câu hỏi ID {question_id}."}
