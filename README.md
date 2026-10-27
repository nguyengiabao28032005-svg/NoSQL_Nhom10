# ĐỒ ÁN CƠ SỞ DỮ LIỆU NoSQL - ĐỀ TÀI 05
# HỆ THỐNG THI TRẮC NGHIỆM & BẢNG XẾP HẠNG THỜI GIAN THỰC (REAL-TIME LEADERBOARD)

> **Môn học:** Cơ Sở Dữ Liệu NoSQL  
> **Giảng viên hướng dẫn:** ThS. Trần Bình  
> **Đề tài 05:** Xây dựng hệ thống Bảng xếp hạng thời gian thực (Real-time Leaderboard) với Redis  
> **Công nghệ áp dụng:** Redis 7 (Sorted Sets, Hash, List, Set, String, Pub/Sub, Keyspace Notifications), FastAPI (Python 3.11), Server-Sent Events (SSE), HTML5/CSS3/Vanilla JS (CSS Transform translateY animation).

---

## 📌 HỒ SƠ NỘP BÀI CUỐI KHÓA (THEO YÊU CẦU ĐỒ ÁN)

Thư mục dự án đã được tổ chức quy chuẩn theo đúng 3 yêu cầu nộp bài của Giảng viên:

| STT | Yêu cầu nộp bài | Thư mục / File tương ứng | Mô tả nội dung |
|:---:|---|---|---|
| **1** | **Hồ sơ đặc tả** | [`docs/`](docs/)<br>↳ [`docs/Ho_So_Dac_Ta_He_Thong.md`](docs/Ho_So_Dac_Ta_He_Thong.md) | Tài liệu đặc tả hệ thống toàn diện: Bối cảnh, Yêu cầu nghiệp vụ, Thiết kế kiến trúc 3 tầng, Mô hình CSDL Redis (Key pattern, Big-O), Đặc tả 18 RESTful APIs, Thuật toán Tie-Breaking & Anti-cheat. |
| **2** | **Slide PowerPoint** | [`slides/`](slides/)<br>↳ [`slides/Slide_Thuyet_Trinh_Do_An.md`](slides/Slide_Thuyet_Trinh_Do_An.md) | Dàn ý báo cáo thuyết minh chuẩn học thuật gồm 14 slides hoàn chỉnh: Đặt vấn đề, Mục tiêu, Kiến trúc, Cấu trúc dữ liệu Redis, Giải thuật xếp hạng, Chống gian lận, Demo và Đánh giá hiệu năng. |
| **3** | **Source code dự án + Database** | [`app/`](app/) & [`static/`](static/)<br>↳ [`database/`](database/) & [`scripts/`](scripts/) | Toàn bộ mã nguồn Backend FastAPI, Frontend CSS translateY animation mượt mà, file cấu hình container `docker-compose.yml`, script phục hồi CSDL tự động `database/restore_db.py` và hướng dẫn backup/restore. |

---

## 1. CẤU TRÚC THƯ MỤC TỔNG THỂ DỰ ÁN

```
DoAn-NoSQL/
├── docs/                                # [YÊU CẦU 1] HỒ SƠ ĐẶC TẢ HỆ THỐNG
│   ├── Ho_So_Dac_Ta_He_Thong.md         # Bản đặc tả kỹ thuật chi tiết toàn bộ hệ thống
│   └── README.md                        # Hướng dẫn xem và xuất tài liệu PDF/Word
├── slides/                              # [YÊU CẦU 2] SLIDE BÁO CÁO POWERPOINT
│   ├── Slide_Thuyet_Trinh_Do_An.md      # Dàn ý chi tiết 14 slide báo cáo thuyết minh đồ án
│   └── README.md                        # Hướng dẫn tạo slide trình chiếu
├── database/                            # [YÊU CẦU 3] CƠ SỞ DỮ LIỆU & BACKUP
│   ├── restore_db.py                    # Script một chạm phục hồi toàn bộ CSDL mẫu vào Redis
│   └── backup_restore_guide.md          # Hướng dẫn kỹ thuật backup & restore (RDB, AOF)
├── app/                                 # [YÊU CẦU 3] MÃ NGUỒN BACKEND (FASTAPI)
│   ├── main.py                          # Khởi tạo FastAPI, CORS, mount Static và cấu hình No-Cache
│   ├── db.py                            # Quản lý Redis Async & Sync Connection Pool
│   ├── schemas.py                       # Pydantic Schemas định nghĩa chuẩn dữ liệu Request/Response
│   └── routers/
│       ├── players.py                   # RESTful CRUD Người chơi (sắp xếp ID tăng dần 1 -> 150)
│       ├── questions.py                 # RESTful CRUD Câu hỏi thi & Danh mục Môn học an toàn
│       ├── games.py                     # Quản lý trận đấu, nộp bài, chấm điểm, chống gian lận
│       ├── leaderboard.py               # Truy vấn BXH Top 10, Around-Me, Thứ hạng cá nhân
│       ├── stream.py                    # Server-Sent Events (SSE) /stream/{gid} & Keyspace Listener
│       └── admin_api.py                 # API kích hoạt nạp dữ liệu mẫu nhanh từ giao diện
├── static/                              # [YÊU CẦU 3] MÃ NGUỒN FRONTEND
│   ├── index.html                       # Giao diện thi trắc nghiệm & Bảng xếp hạng Live Top 10
│   ├── admin.html                       # Bảng điều khiển quản trị (Môn học, Đề thi, Thí sinh)
│   └── style.css                        # CSS hiệu ứng chuyển động trượt mượt mà (translateY 48px)
├── scripts/
│   └── seed.py                          # Script khởi tạo 150 thí sinh, 100 câu hỏi, 10 trận đấu
├── docker-compose.yml                   # Container Redis 7 (chế độ lưu trữ bền vững AOF)
├── requirements.txt                     # Danh sách thư viện Python phụ thuộc
├── .gitignore                           # Loại trừ file rác, venv, cache khi đẩy lên GitHub
└── README.md                            # Hướng dẫn tổng quan & cài đặt vận hành
```

---

## 2. CẤU TRÚC DỮ LIỆU REDIS ÁP DỤNG TRONG ĐỒ ÁN

| Cấu trúc dữ liệu Redis | Key Pattern | Lệnh Redis chính | Mục đích sử dụng |
|---|---|---|---|
| **String** | `seq:player`, `seq:question`, `seq:game` | `INCR`, `SET`, `GET` | Sinh khóa chính tự động tăng nguyên tử cho các thực thể. |
| **Hash** | `player:{id}` | `HSET`, `HGETALL`, `HINCRBY` | Lưu trữ hồ sơ người chơi (username, họ tên, email, avatar,...). |
| **Hash** | `question:{id}` | `HSET`, `HGETALL` | Lưu trữ nội dung câu hỏi, 4 phương án A/B/C/D, đáp án đúng và điểm. |
| **Hash** | `game:{id}` | `HSET`, `HGETALL` | Lưu thông tin trận đấu (tên đề thi, trạng thái `running`/`finished`). |
| **Hash** | `game:{gid}:answers:{pid}` | `HSET`, `HGETALL` | Lưu phương án thí sinh đã chọn trong trận đấu. |
| **List** | `game:{gid}:questions` | `RPUSH`, `LRANGE` | Lưu danh sách ID câu hỏi trong đề thi theo đúng thứ tự. |
| **Set** | `categories` | `SADD`, `SMEMBERS`, `SREM` | Quản lý danh mục các môn học trong hệ thống. |
| **Set** | `category:{cat}:questions` | `SADD`, `SMEMBERS` | Chỉ mục câu hỏi theo từng môn học. |
| **Set** | `game:{gid}:players` | `SADD`, `SCARD`, `SMEMBERS` | Quản lý danh sách thí sinh đã tham gia trận đấu. |
| **Set** | `game:{gid}:answered:{pid}` | `SADD`, `SISMEMBER` | **Chống gian lận:** Kiểm tra và chặn trả lời trùng lặp một câu hỏi. |
| **Sorted Set (ZSET)** | `leaderboard:game:{gid}` | `ZADD`, `ZINCRBY`, `ZREVRANGE`, `ZREVRANK`, `ZSCORE` | Bảng xếp hạng trận đấu, tự động sắp xếp theo điểm số từ cao xuống thấp. |
| **Sorted Set (ZSET)** | `leaderboard:global` | `ZADD`, `ZINCRBY`, `ZREVRANGE`, `ZREVRANK`, `ZSCORE` | Bảng xếp hạng toàn cầu tích lũy điểm qua tất cả các trận đấu. |
| **Pub/Sub** | `channel:game:{gid}` | `PUBLISH`, `SUBSCRIBE` | Kênh phát tín hiệu thời gian thực khi có người ghi điểm hoặc đổi hạng. |
| **Keyspace Notifications** | `__keyevent@0__:zincr*`, `__keyevent@0__:zadd*` | `PSUBSCRIBE` (cờ `KEA`) | Tự động phát hiện khi admin can thiệp điểm số trực tiếp qua terminal `redis-cli`. |

---

## 3. HƯỚNG DẪN CÀI ĐẶT VÀ VẬN HÀNH HỆ THỐNG

### Bước 1: Khởi động Redis Container
Nếu sử dụng Docker Desktop, mở terminal tại thư mục gốc và chạy:
```powershell
docker compose up -d
```
*(Hoặc sử dụng dịch vụ Redis 7 đang chạy sẵn trên máy host tại cổng `6379`).*

### Bước 2: Thiết lập môi trường ảo Python
```powershell
# 1. Tạo môi trường ảo (nếu chưa có)
python -m venv venv

# 2. Kích hoạt môi trường ảo
.\venv\Scripts\Activate.ps1

# 3. Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### Bước 3: Phục hồi Cơ sở dữ liệu mẫu chuẩn (Seed / Restore Database)
Chạy script để nạp ngay **150 thí sinh, 100 câu hỏi và 10 trận đấu** vào Redis:
```powershell
python database/restore_db.py
```
*(Script được thiết kế an toàn, chỉ dọn các key thuộc namespace dự án, tuyệt đối không dùng `FLUSHALL` để bảo vệ dữ liệu khác).*

### Bước 4: Khởi động Web Server FastAPI
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Server sẽ sẵn sàng phục vụ tại: **`http://127.0.0.1:8000`**.

---

## 4. TRUY CẬP VÀ SỬ DỤNG HỆ THỐNG

| Giao diện / Chức năng | Đường dẫn URL | Mô tả chức năng |
|---|---|---|
| **Hệ thống Thi Trắc Nghiệm** | [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html) | Giao diện thi đấu cho thí sinh: Chọn môn thi, nộp bài, xem đáp án đã chọn, Bảng xếp hạng Top 10 động với animation mượt mà, mục Vị trí xung quanh bạn. |
| **Bảng Quản Trị Hệ Thống (Admin)** | [http://localhost:8000/static/admin.html](http://localhost:8000/static/admin.html) | Quản lý Thí sinh, Câu hỏi, Trận đấu (Bắt đầu, Kết thúc, Mở lại trận đấu), Nút nạp nhanh dữ liệu mẫu chuẩn. |
| **Tài liệu API Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Kiểm thử trực tiếp toàn bộ 18 RESTful API endpoints với tài liệu chi tiết. |
| **Kiểm tra trạng thái hệ thống** | [http://localhost:8000/health](http://localhost:8000/health) | Trả về JSON trạng thái kết nối Redis PING/PONG. |

---


