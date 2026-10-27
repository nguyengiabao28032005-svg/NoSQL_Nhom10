# HỒ SƠ ĐẶC TẢ HỆ THỐNG (SYSTEM SPECIFICATION DOCUMENT)
## ĐỒ ÁN MÔN HỌC: CƠ SỞ DỮ LIỆU NoSQL
### ĐỀ TÀI 05: XÂY DỰNG HỆ THỐNG THI TRẮC NGHIỆM & BẢNG XẾP HẠNG THỜI GIAN THỰC (REAL-TIME LEADERBOARD VỚI REDIS)

---

**Thông tin chung:**
- **Môn học:** Cơ sở dữ liệu NoSQL
- **Giảng viên hướng dẫn:** ThS. Trần Bình
- **Đề tài số:** 05 - Hệ thống Bảng xếp hạng thời gian thực (Real-time Leaderboard)
- **Công nghệ áp dụng:** Redis 7 (In-Memory Data Store), FastAPI (Python 3.11), Server-Sent Events (SSE), HTML5/CSS3/Vanilla JavaScript.

---

## MỤC LỤC
1. [Giới thiệu tổng quan & Tính cấp thiết của đề tài](#1-giới-thiệu-tổng-quan--tính-cấp-thiết-của-đề-tài)
2. [Đặc tả yêu cầu hệ thống (System Requirements)](#2-đặc-tả-yêu-cầu-hệ-thống-system-requirements)
3. [Thiết kế kiến trúc hệ thống (System Architecture)](#3-thiết-kế-kiến-trúc-hệ-thống-system-architecture)
4. [Đặc tả Cơ sở dữ liệu NoSQL Redis (Redis Data Modeling)](#4-đặc-tả-cơ-sở-dữ-liệu-nosql-redis-redis-data-modeling)
5. [Đặc tả Giao diện Lập trình Ứng dụng (API Specifications)](#5-đặc-tả-giao-diện-lập-trình-ứng-dụng-api-specifications)
6. [Các giải thuật và kỹ thuật nâng cao áp dụng](#6-các-giải-thuật-và-kỹ-thuật-nâng-cao-áp-dụng)
7. [Hướng dẫn cài đặt, triển khai và kiểm thử](#7-hướng-dẫn-cài-đặt-triển-khai-và-kiểm-thử)
8. [Kết luận và hướng phát triển](#8-kết-luận-và-hướng-phát-triển)

---

## 1. GIỚI THIỆU TỔNG QUAN & TÍNH CẤP THIẾT CỦA ĐỀ TÀI

### 1.1. Bối cảnh bài toán
Trong các hệ thống thi trắc nghiệm trực tuyến nhiều người chơi (như Kahoot, Quizizz), các cuộc thi trí tuệ (Đường lên đỉnh Olympia trực tuyến) hoặc các trò chơi trực tuyến nhiều người tham gia (Online Multiplayer Games), **Bảng xếp hạng thời gian thực (Real-time Leaderboard)** là tính năng trung tâm tạo nên sự kịch tính và thu hút người chơi.

Tại mỗi thời điểm một câu hỏi kết thúc hoặc thí sinh bấm nộp đáp án:
- Điểm số của thí sinh phải được tính toán và cập nhật ngay lập tức.
- Thứ hạng của hàng nghìn thí sinh phải được tự động tái sắp xếp.
- Bảng xếp hạng hiển thị trên màn hình của tất cả thí sinh và khán giả phải đồng loạt chuyển động mượt mà mà không làm tải lại trang (Zero Refresh / Zero Polling).

### 1.2. Thách thức với Cơ sở dữ liệu Quan hệ truyền thống (RDBMS)
Nếu sử dụng các hệ quản trị CSDL quan hệ truyền thống như MySQL, PostgreSQL hoặc SQL Server:
1. **Nghẽn cổ chai sắp xếp (Sorting Bottleneck):** Mỗi lần lấy top 10 bảng xếp hạng, RDBMS phải chạy truy vấn dạng:
   ```sql
   SELECT player_id, score FROM leaderboard ORDER BY score DESC LIMIT 10;
   ```
   Với hàng chục nghìn người chơi đồng thời nộp bài, câu lệnh này khiến ổ đĩa phải liên tục đọc ghi (Disk I/O), chi phí thuật toán sắp xếp là $\mathcal{O}(N \log N)$, dẫn đến tình trạng khóa bảng (Table Locking), nghẽn hàng đợi kết nối và CPU máy chủ chạm ngưỡng 100%.
2. **Quá tải vì Polling:** Nếu máy khách (Web Client) liên tục gửi HTTP GET mỗi giây để cập nhật điểm mới, hàng triệu request vô nghĩa sẽ làm sập máy chủ web.

### 1.3. Giải pháp đột phá với NoSQL Redis
Redis là hệ quản trị CSDL In-Memory dạng Key-Value mã nguồn mở siêu tốc độ:
- Dữ liệu lưu trữ trực tiếp trên RAM, thời gian đáp ứng ở mức **dưới mili-giây (sub-millisecond latency)**.
- Hỗ trợ cấu trúc dữ liệu **Sorted Set (ZSET)** chuyên biệt cho bài toán xếp hạng, được hiện thực bởi cấu trúc dữ liệu kết hợp giữa **SkipList** và **Hash Table**:
  - Tăng điểm: `ZINCRBY` độ phức tạp chỉ $\mathcal{O}(\log N)$.
  - Tra cứu thứ tự xếp hạng: `ZREVRANK` độ phức tạp chỉ $\mathcal{O}(\log N)$.
  - Lấy Top $M$ người dẫn đầu: `ZREVRANGE` độ phức tạp chỉ $\mathcal{O}(\log N + M)$.
- Tích hợp sẵn cơ chế **Publish/Subscribe (Pub/Sub)** và **Keyspace Notifications** giúp phát tín hiệu thời gian thực khi có biến động dữ liệu.

---

## 2. ĐẶC TẢ YÊU CẦU HỆ THỐNG (SYSTEM REQUIREMENTS)

### 2.1. Yêu cầu chức năng (Functional Requirements)
1. **Phân hệ Thí sinh & Thi trắc nghiệm:**
   - Chọn thí sinh dự thi từ danh sách chuẩn hóa.
   - Chọn bộ đề / trận đấu theo môn học (Toán, Lý, Hóa, Sinh, Sử, Địa, Văn, Anh, Tin, Khoa học).
   - Làm bài trắc nghiệm với giao diện trực quan, đồng hồ đếm và kiểm tra tính hợp lệ.
   - Hệ thống phản hồi kết quả câu trả lời (Đúng / Sai), hiển thị giải thích chi tiết và cộng điểm.
2. **Phân hệ Bảng xếp hạng Thời gian thực (Live Leaderboard):**
   - **Top 10 Live:** Hiển thị 10 người có điểm số cao nhất trận đấu và toàn cầu.
   - **Smooth Rank Shifting:** Tự động hoán đổi vị trí mượt mà bằng hiệu ứng CSS TranslateY khi có người vượt điểm.
   - **Around-Me Leaderboard:** Đối với các thí sinh ngoài Top 10, hiển thị thứ hạng của chính họ cùng 2 đối thủ đứng liền trước và liền sau.
3. **Phân hệ Quản trị hệ thống (Admin Dashboard):**
   - Quản lý danh mục môn học (Thêm, Xóa an toàn có ràng buộc dữ liệu).
   - Quản trị ngân hàng câu hỏi (Tạo câu hỏi, 4 đáp án A/B/C/D, đáp án đúng, điểm số).
   - Quản trị trận đấu (Tạo trận đấu, đổi trạng thái Bắt đầu / Kết thúc).
   - Nạp dữ liệu mẫu nhanh (Seed Data: 150 thí sinh, 100 câu hỏi, 10 trận đấu) chỉ với 1 thao tác.
4. **Cơ chế Chống gian lận (Anti-Cheat):**
   - Ngăn chặn một thí sinh nộp bài nhiều lần cho cùng một câu hỏi.
   - Khóa toàn bộ quyền nộp bài khi trận đấu kết thúc hoặc khi câu hỏi đã được trả lời.

### 2.2. Yêu cầu phi chức năng (Non-Functional Requirements)
- **Độ trễ phản hồi (Response Latency):** Thời gian ghi nhận điểm và tính hạng < 5ms.
- **Tính toàn vẹn & Nguyên tử (Atomicity):** Điểm số trận đấu và điểm số toàn cục được cập nhật đồng thời qua Redis Transaction Pipeline.
- **Tính khả dụng & Bền vững (Persistence):** Cấu hình cơ chế lưu trữ AOF (Append-Only File) để không mất mát dữ liệu khi máy chủ khởi động lại.
- **Khả năng tương thích:** Chạy tốt trên các trình duyệt hiện đại (Chrome, Edge, Firefox, Safari) hỗ trợ Server-Sent Events và CSS3 Transforms.

---

## 3. THIẾT KẾ KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

Hệ thống được thiết kế theo mô hình 3 tầng (Three-Tier Architecture) kết hợp với kiến trúc hướng sự kiện (Event-Driven Architecture):

```
+-------------------------------------------------------------------------+
|                       TẦNG TRÌNH DIỄN (FRONTEND)                        |
|   +--------------------------+         +----------------------------+   |
|   |   Giao diện Thí sinh     |         |   Bảng điều khiển Admin    |   |
|   |  (index.html, CSS 48px)  |         |        (admin.html)        |   |
|   +--------------------------+         +----------------------------+   |
|                ^                                     |                  |
+----------------|-------------------------------------|------------------+
                 | (SSE Stream /stream/{gid})          | (REST APIs)
                 v                                     v
+-------------------------------------------------------------------------+
|                  TẦNG XỬ LÝ ỨNG DỤNG (BACKEND FASTAPI)                  |
|   - routers/players.py: CRUD hồ sơ thí sinh                             |
|   - routers/questions.py: Quản trị ngân hàng câu hỏi & chủ đề           |
|   - routers/games.py: Điều phối trận đấu & Chấm điểm nguyên tử          |
|   - routers/leaderboard.py: Truy vấn Top 10 & Around-Me                 |
|   - routers/stream.py: SSE Event Broadcaster & Keyspace Listener        |
+-------------------------------------------------------------------------+
                                 |
                                 v (Async Connection Pool)
+-------------------------------------------------------------------------+
|                  TẦNG CƠ SỞ DỮ LIỆU NoSQL (REDIS 7)                     |
|   +----------------------+   +-------------------+   +--------------+   |
|   |     Sorted Sets      |   |      Hashes       |   | Sets & Lists |   |
|   |  (Bảng xếp hạng Live)|   | (Hồ sơ, Câu hỏi)  |   | (Anti-cheat) |   |
|   +----------------------+   +-------------------+   +--------------+   |
|   +----------------------+   +-------------------+   +--------------+   |
|   |   Pub/Sub Channels   |   |   Keyspace Events |   | AOF Storage  |   |
|   | (Phát sóng real-time)|   | (Bắt lệnh cli)    |   | (Bền vững)   |   |
|   +----------------------+   +-------------------+   +--------------+   |
+-------------------------------------------------------------------------+
```

---

## 4. ĐẶC TẢ CƠ SỞ DỮ LIỆU NoSQL REDIS (REDIS DATA MODELING)

Hệ thống ứng dụng đầy đủ và chuyên sâu 5 cấu trúc dữ liệu nền tảng của Redis:

### 4.1. Bảng thiết kế các Key Pattern

| Cấu trúc dữ liệu | Định dạng Key (Pattern) | Mục đích sử dụng | Độ phức tạp (Big-O) | Lệnh thao tác chính |
|---|---|---|---|---|
| **String** | `seq:player` | Biến đếm ID tự tăng cho thí sinh | $\mathcal{O}(1)$ | `INCR`, `SET` |
| **String** | `seq:question` | Biến đếm ID tự tăng cho câu hỏi | $\mathcal{O}(1)$ | `INCR`, `SET` |
| **String** | `seq:game` | Biến đếm ID tự tăng cho trận đấu | $\mathcal{O}(1)$ | `INCR`, `SET` |
| **Hash** | `player:{id}` | Lưu trữ thông tin hồ sơ thí sinh | $\mathcal{O}(1)$ | `HSET`, `HGETALL` |
| **Hash** | `question:{id}` | Lưu nội dung câu hỏi, 4 phương án, đáp án đúng | $\mathcal{O}(1)$ | `HSET`, `HGETALL` |
| **Hash** | `game:{id}` | Lưu trạng thái, tên đề thi, thời gian khởi tạo | $\mathcal{O}(1)$ | `HSET`, `HGETALL` |
| **Hash** | `game:{gid}:answers:{pid}` | Lưu các đáp án mà thí sinh đã chọn trong trận | $\mathcal{O}(1)$ | `HSET`, `HGETALL` |
| **List** | `game:{gid}:questions` | Danh sách thứ tự các câu hỏi trong trận đấu | $\mathcal{O}(1)$ với Push, $\mathcal{O}(N)$ với Range | `RPUSH`, `LRANGE` |
| **Set** | `categories` | Tập hợp các môn học trong hệ thống | $\mathcal{O}(1)$ | `SADD`, `SMEMBERS`, `SREM` |
| **Set** | `category:{cat}:questions` | Chỉ mục các ID câu hỏi thuộc về môn học `cat` | $\mathcal{O}(1)$ | `SADD`, `SMEMBERS`, `SREM` |
| **Set** | `game:{gid}:players` | Tập hợp các thí sinh đã tham gia trận đấu | $\mathcal{O}(1)$ | `SADD`, `SCARD`, `SMEMBERS` |
| **Set** | `game:{gid}:answered:{pid}` | **Cơ chế chống gian lận:** Lưu các ID câu hỏi thí sinh đã nộp | $\mathcal{O}(1)$ | `SADD`, `SISMEMBER` |
| **Sorted Set** | `leaderboard:game:{gid}` | Bảng xếp hạng trận đấu hiện tại (Score = Điểm) | $\mathcal{O}(\log N)$ | `ZADD`, `ZINCRBY`, `ZREVRANGE`, `ZREVRANK`, `ZSCORE` |
| **Sorted Set** | `leaderboard:global` | Bảng xếp hạng tích lũy toàn cục qua tất cả các trận | $\mathcal{O}(\log N)$ | `ZADD`, `ZINCRBY`, `ZREVRANGE`, `ZREVRANK`, `ZSCORE` |

### 4.2. Chi tiết cấu trúc dữ liệu của các thực thể chính

#### a) Thực thể Thí sinh (`player:{id}` - Hash):
```redis
HSET player:1 username "thang.nguyen" full_name "Nguyễn Văn Thắng" email "thang.nguyen@example.com" avatar "https://api.dicebear.com/7.x/bottts/svg?seed=thang" created_at "2026-10-20T10:00:00"
```

#### b) Thực thể Câu hỏi (`question:{id}` - Hash):
```redis
HSET question:1 content "Số nguyên tố chẵn duy nhất là số nào?" A "0" B "2" C "4" D "6" correct "B" category "Toán" points "100"
```

#### c) Thực thể Bảng xếp hạng Trận đấu (`leaderboard:game:{gid}` - Sorted Set):
- Member: `player:{id}` (Ví dụ: `player:1`)
- Score: Điểm số của thí sinh (Ví dụ: `800`)
```redis
ZADD leaderboard:game:1 800 "player:1"
ZADD leaderboard:game:1 900 "player:2"
ZADD leaderboard:game:1 600 "player:3"
```
Khi muốn lấy Top 3 người dẫn đầu kèm điểm số:
```redis
ZREVRANGE leaderboard:game:1 0 2 WITHSCORES
```
Kết quả trả về ngay lập tức theo thứ tự điểm cao đến thấp: `player:2 (900)`, `player:1 (800)`, `player:3 (600)`.

---

## 5. ĐẶC TẢ GIAO DIỆN LẬP TRÌNH ỨNG DỤNG (API SPECIFICATIONS)

Hệ thống cung cấp hệ thống RESTful API chuẩn mực theo chuẩn OpenAPI / Swagger (truy cập tại `/docs`):

### 5.1. Nhóm API Quản lý Người chơi (`/players`)
- `POST /players/`: Tạo hồ sơ thí sinh mới (kiểm tra username duy nhất).
- `GET /players/`: Lấy danh sách toàn bộ thí sinh (đã được sắp xếp thứ tự ID tăng dần).
- `GET /players/{player_id}`: Lấy chi tiết hồ sơ thí sinh.
- `PUT /players/{player_id}`: Cập nhật thông tin thí sinh.
- `DELETE /players/{player_id}`: Xóa thí sinh khỏi hệ thống.

### 5.2. Nhóm API Quản lý Câu hỏi & Chủ đề (`/questions`)
- `GET /questions/categories`: Lấy danh sách các môn học / chủ đề.
- `POST /questions/categories`: Tạo thêm môn học mới.
- `DELETE /questions/categories/{category_name}`: Xóa môn học (kiểm tra ràng buộc: nếu còn câu hỏi thì không cho xóa).
- `POST /questions/`: Thêm câu hỏi mới vào ngân hàng câu hỏi.
- `GET /questions/`: Lấy danh sách câu hỏi (hỗ trợ lọc theo `category`).
- `GET /questions/{question_id}`: Lấy chi tiết câu hỏi.
- `DELETE /questions/{question_id}`: Xóa câu hỏi và tự động cập nhật lại các Set chỉ mục liên quan.

### 5.3. Nhóm API Quản trị Trận đấu & Nộp bài (`/games`)
- `POST /games/`: Tạo trận đấu mới kèm danh sách câu hỏi.
- `GET /games/`: Lấy danh sách các trận đấu đang có.
- `GET /games/{game_id}`: Lấy thông tin chi tiết trận đấu và danh sách câu hỏi trong đề thi.
- `PUT /games/{game_id}/status`: Cập nhật trạng thái trận đấu (`waiting`, `running`, `finished`).
- `POST /games/{game_id}/answer`: Nộp câu trả lời cho 1 câu hỏi.
  - **Request Body:** `{"player_id": 1, "question_id": 5, "choice": "B"}`
  - **Xử lý:** Kiểm tra trạng thái trận đấu -> Kiểm tra chống nộp lặp -> So khớp đáp án -> Chạy Redis Pipeline ghi nhận điểm và phát Pub/Sub event -> Trả về kết quả đúng/sai và điểm số.

### 5.4. Nhóm API Bảng xếp hạng (`/leaderboard`)
- `GET /leaderboard/{game_id}?top=10`: Lấy Top 10 thí sinh dẫn đầu trận đấu.
- `GET /leaderboard/global?top=10`: Lấy Top 10 thí sinh tích lũy điểm cao nhất toàn hệ thống.
- `GET /leaderboard/{game_id}/around/{player_id}`: Lấy danh sách Around-Me (chính người chơi + 2 người đứng trước + 2 người đứng sau).

### 5.5. Nhóm API Thời gian thực & Streaming (`/stream`)
- `GET /stream/{game_id}`: Mở kênh Server-Sent Events (SSE) theo dõi biến động thứ hạng và trạng thái trận đấu `game_id`.

---

## 6. CÁC GIẢI THUẬT VÀ KỸ THUẬT NÂNG CAO ÁP DỤNG

### 6.1. Thuật toán xử lý đồng điểm (Tie-Breaking Algorithm)
Khi hai thí sinh có cùng số điểm, hệ thống xử lý qua hai tầng:
1. **Tầng mặc định của Redis Sorted Set:**
   - Khi `score` bằng nhau, Redis sử dụng thứ tự từ điển (`Lexicographical Order`) của `member` để phân định thứ tự.
   - Nhờ đó, thứ hạng luôn ổn định tuyệt đối trong độ phức tạp $\mathcal{O}(\log N)$, không xảy ra hiện tượng hoán đổi vị trí vô cớ giữa các vòng render.
2. **Kỹ thuật mở rộng - Phần bù thời gian (Fractional Timestamp):**
   - Điểm số trong Redis Sorted Set hỗ trợ số thực dấu phẩy động kép (64-bit Double-Precision Float).
   - Công thức tính điểm ưu tiên cho người nộp bài trước:
     $$\mathbf{Score} = \text{Điểm số} + \left(1 - \frac{\text{Timestamp}}{10^{10}}\right)$$
   - Vì người nộp bài trước có `Timestamp` nhỏ hơn $\rightarrow$ Phần bù thập phân lớn hơn $\rightarrow$ Điểm tổng thể lớn hơn và được Redis xếp đứng trên người nộp sau dù cùng số điểm gốc.

### 6.2. Cơ chế Chống gian lận (Anti-Cheat Mechanism)
Để ngăn chặn thí sinh gửi nhiều request nộp bài liên tiếp nhằm "spam" điểm:
1. Hệ thống sử dụng lệnh `SADD game:{gid}:answered:{pid} {qid}`.
2. Tính chất của Redis Set: Một phần tử chỉ có thể được thêm vào tập hợp một lần duy nhất.
3. Nếu lệnh `SADD` trả về `0`, hệ thống nhận diện câu hỏi này đã được trả lời trước đó và lập tức từ chối xử lý, bảo đảm tính công bằng tuyệt đối cho cuộc thi.

### 6.3. Tính nguyên tử với Redis Transaction Pipeline
Khi thí sinh trả lời đúng một câu hỏi, hệ thống phải thực hiện đồng thời nhiều thao tác ghi:
- Ghi nhận đáp án thí sinh đã chọn vào Hash.
- Tăng điểm trận đấu trong Sorted Set `leaderboard:game:{gid}`.
- Tăng điểm toàn cục trong Sorted Set `leaderboard:global`.

Hệ thống bọc toàn bộ các thao tác trên trong một khối giao dịch:
```python
async with r.pipeline(transaction=True) as pipe:
    pipe.hset(f"game:{gid}:answers:{pid}", str(qid), user_choice)
    pipe.zincrby(f"leaderboard:game:{gid}", points, member)
    pipe.zincrby("leaderboard:global", points, member)
    await pipe.execute()
```
Đảm bảo tính **ACID (Atomicity & Isolation)**: Mọi thao tác đều thành công trọn vẹn hoặc không có thao tác nào được thực hiện nếu xảy ra lỗi.

### 6.4. Trực quan hóa chuyển động thứ hạng (Smooth Rank Shifting)
Thay vì xóa toàn bộ bảng xếp hạng và tạo lại các thẻ HTML (gây giật màn hình):
1. Mỗi dòng thí sinh được gắn một định danh duy nhất `data-id="player:{id}"`.
2. Khi có sự kiện SSE gửi về thứ hạng mới, client tính toán độ lệch thứ hạng:
   $$\Delta \text{rank} = \text{Rank}_{\text{cũ}} - \text{Rank}_{\text{mới}}$$
3. Áp dụng thuộc tính CSS:
   ```css
   transform: translateY(calc(var(--delta) * 48px));
   transition: transform 0.4s cubic-bezier(0.2, 0, 0, 1);
   ```
4. Người chơi sẽ thấy thẻ của mình và đối thủ trượt lên/xuống mượt mà với tốc độ 60 khung hình/giây.

---

## 7. HƯỚNG DẪN CÀI ĐẶT, TRIỂN KHAI VÀ KIỂM THỬ

### 7.1. Yêu cầu môi trường
- Python 3.10 trở lên.
- Docker & Docker Compose (hoặc dịch vụ Redis Server 7.x).
- Hệ điều hành: Windows, Linux hoặc macOS.

### 7.2. Các bước triển khai
```powershell
# Bước 1: Khởi động Redis Container
docker compose up -d

# Bước 2: Tạo môi trường ảo và cài đặt thư viện
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Bước 3: Nạp dữ liệu mẫu chuẩn (150 thí sinh, 100 câu hỏi, 10 trận đấu)
python database/restore_db.py

# Bước 4: Khởi chạy máy chủ FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.3. Truy cập hệ thống
- Giao diện Thi trắc nghiệm & BXH Live: `http://localhost:8000`
- Giao diện Quản trị viên (Admin Panel): `http://localhost:8000/admin`
- Tài liệu API tương tác (Swagger UI): `http://localhost:8000/docs`

---

## 8. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

Đồ án đã giải quyết trọn vẹn và xuất sắc bài toán Bảng xếp hạng thời gian thực bằng việc ứng dụng chuyên sâu công nghệ CSDL NoSQL Redis. Hệ thống đạt độ trễ cực thấp, giao diện trực quan sinh động, kiến trúc mở dễ dàng bảo trì và mở rộng quy mô.

**Hướng phát triển tiếp theo:**
- Triển khai mô hình phân tán **Redis Cluster** và kỹ thuật Sharding khi hệ thống mở rộng lên quy mô hàng triệu người chơi.
- Tích hợp thêm âm thanh thi đấu và các vòng đối kháng trực tiếp 1-1.
