# HƯỚNG DẪN SAO LƯU & PHỤC HỒI CƠ SỞ DỮ LIỆU REDIS (BACKUP & RESTORE)

Tài liệu này hướng dẫn các phương thức sao lưu (Backup) và phục hồi (Restore) dữ liệu cho Hệ thống Thi trắc nghiệm & Bảng xếp hạng Real-time Redis.

---

## 1. PHƯƠNG THỨC 1: SỬ DỤNG SCRIPT PHỤC HỒI DỮ LIỆU TỰ ĐỘNG (KHUYẾN NGHỊ)

Đây là cách nhanh nhất và an toàn nhất để thiết lập toàn bộ CSDL trên bất kỳ máy nào:

### Cách thực hiện:
1. Đảm bảo dịch vụ Redis đang chạy (port `6379`).
2. Kích hoạt môi trường ảo Python và chạy lệnh:
```powershell
python database/restore_db.py
```
*(hoặc `python scripts/seed.py`)*

### Dữ liệu được phục hồi bao gồm:
- **150 Người chơi** (ID từ 1 đến 150) với đầy đủ họ tên, email, avatar ngẫu nhiên.
- **10 Môn học**: Toán, Lý, Hóa, Sinh, Sử, Địa, Văn, Anh, Tin, Khoa học & Đời sống.
- **100 Câu hỏi trắc nghiệm** (10 câu/môn, 4 đáp án A/B/C/D, giải thích và điểm thưởng).
- **10 Trận đấu** đã được gắn các bộ câu hỏi tương ứng và mở trạng thái `running`.
- **Sorted Sets**: BXH từng trận (`leaderboard:game:{gid}`) và BXH Toàn cục (`leaderboard:global`).

---

## 2. PHƯƠNG THỨC 2: SAO LƯU BẰNG CƠ CHẾ RDB (REDIS DATABASE SNAPSHOT)

RDB tạo ra một file snapshot nhị phân (`dump.rdb`) tại một thời điểm nhất định.

### Bước 1: Tạo bản sao lưu (Backup)
Mở terminal và kết nối vào Redis (qua `redis-cli` hoặc Docker container):
```powershell
# Nếu chạy Redis bằng Docker:
docker exec redis redis-cli BGSAVE

# Nếu chạy Redis trực tiếp:
redis-cli BGSAVE
```
Redis sẽ tạo file `dump.rdb` trong thư mục làm việc của Redis (mặc định là `/data` trong Docker).

Để copy file `dump.rdb` ra thư mục `database/` trên máy host:
```powershell
docker cp redis:/data/dump.rdb ./database/dump.rdb
```

### Bước 2: Phục hồi từ bản sao lưu (Restore)
1. Dừng Redis service: `docker compose down` hoặc stop service.
2. Đặt file `dump.rdb` vào thư mục data của Redis.
3. Khởi động lại Redis:
```powershell
docker compose up -d
```
Redis sẽ tự động đọc file `dump.rdb` và phục hồi toàn bộ dữ liệu vào RAM khi khởi động.

---

## 3. PHƯƠNG THỨC 3: SAO LƯU BẰNG CƠ CHẾ AOF (APPEND-ONLY FILE)

Đồ án đã cấu hình sẵn chế độ lưu trữ **AOF** trong file `docker-compose.yml`:
```yaml
command: redis-server --appendonly yes --notify-keyspace-events KEA
```
- **Ưu điểm:** Ghi log tuần tự mọi thao tác ghi (`HSET`, `ZINCRBY`, `SADD`,...). Nếu hệ thống bị tắt đột ngột, Redis sẽ phát lại log để khôi phục 100% dữ liệu mà không mất mát.
- Thư mục lưu trữ AOF được ánh xạ tự động vào volume `redis_data` của Docker.

---

## 4. BẢNG TỔNG HỢP CÁC KEY CHÍNH TRONG DATABASE

| Kiểu dữ liệu | Định dạng Key | Giải thích |
|---|---|---|
| **String** | `seq:player`, `seq:question`, `seq:game` | Biến đếm ID tự tăng nguyên tử |
| **Hash** | `player:{id}` | Thông tin chi tiết hồ sơ thí sinh |
| **Hash** | `question:{id}` | Nội dung câu hỏi và 4 đáp án A/B/C/D |
| **Hash** | `game:{id}` | Trạng thái và thông tin trận đấu |
| **Hash** | `game:{gid}:answers:{pid}` | Đáp án thí sinh đã nộp |
| **List** | `game:{gid}:questions` | Thứ tự các câu hỏi trong đề thi |
| **Set** | `category:{cat}:questions` | Chỉ mục câu hỏi theo môn học |
| **Set** | `game:{gid}:answered:{pid}` | Chống gian lận: danh sách câu đã trả lời |
| **Sorted Set** | `leaderboard:game:{gid}` | Bảng xếp hạng trận đấu (sắp xếp theo điểm) |
| **Sorted Set** | `leaderboard:global` | Bảng xếp hạng tích lũy toàn cục |
