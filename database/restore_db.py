"""
DATABASE RESTORE / SEED SCRIPT
Đồ án NoSQL - Hệ thống Thi trắc nghiệm & Bảng xếp hạng Real-time Redis
Script này tự động khởi tạo và phục hồi toàn bộ dữ liệu mẫu chuẩn vào Redis:
- 150 Thí sinh (Username, Họ tên, Email, Avatar, Điểm tích lũy)
- 10 Chủ đề môn học
- 100 Câu hỏi trắc nghiệm chất lượng cao
- 10 Trận đấu tương ứng
- Khởi tạo Sorted Sets BXH từng trận và BXH Toàn cầu
"""

import sys
import os

# Thêm đường dẫn thư mục gốc vào sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.seed import main

if __name__ == "__main__":
    print("=================================================================")
    print(" Khởi chạy phục hồi dữ liệu Redis (Restore / Seed Database)")
    print("=================================================================")
    main()
