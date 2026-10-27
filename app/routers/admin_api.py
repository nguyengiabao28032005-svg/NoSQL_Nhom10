from fastapi import APIRouter, HTTPException, status
from scripts.seed import seed_database

router = APIRouter(prefix="/admin-api", tags=["Admin API - Tiện ích quản trị"])

@router.post("/seed", status_code=status.HTTP_200_OK)
def trigger_seed_database(reset: bool = True):
    """
    Nạp dữ liệu mẫu đạt chuẩn định mức:
    - Xóa an toàn các key namespace của đồ án (KHÔNG dùng FLUSHALL)
    - Nạp 150 người chơi, 30 câu hỏi, Game ID=1 với 125 người chơi
    """
    try:
        stats = seed_database(reset=reset)
        return {
            "status": "success",
            "message": "Đã nạp dữ liệu mẫu thành công!",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi nạp dữ liệu: {e}")
