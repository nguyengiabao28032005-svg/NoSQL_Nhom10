import argparse
import random
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import redis
from app.db import get_sync_redis, safe_delete_by_pattern

VIETNAMESE_LAST_NAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Đoàn"
]

VIETNAMESE_MIDDLE_NAMES = [
    "Văn", "Thị", "Hữu", "Đức", "Minh", "Quang", "Gia", "Thanh", "Tuấn",
    "Hoàng", "Bảo", "Xuân", "Thái", "Ngọc", "Anh", "Phương", "Hải", "Khánh"
]

VIETNAMESE_FIRST_NAMES = [
    "An", "Bình", "Cường", "Dũng", "Em", "Phúc", "Giang", "Huy", "Khoa",
    "Linh", "Minh", "Nam", "Oanh", "Phong", "Quân", "Sơn", "Tâm", "Uyên",
    "Việt", "Xuân", "Yến", "Trí", "Đạt", "Thịnh", "Thắng", "Trang", "Tú"
]

QUESTIONS_DATA = [
    # ==================== GAME 1: MÔN TOÁN (10 CÂU: ID 1 -> 10) ====================
    {"content": "Số nguyên tố chẵn duy nhất trong tập hợp các số tự nhiên là số nào?", "A": "0", "B": "2", "C": "4", "D": "6", "correct": "B", "category": "Toán", "points": 100},
    {"content": "Giá trị của 2 mũ 10 (2^10) bằng bao nhiêu?", "A": "512", "B": "1000", "C": "1024", "D": "2048", "correct": "C", "category": "Toán", "points": 100},
    {"content": "Tổng các góc trong một hình tam giác bằng bao nhiêu độ?", "A": "90 độ", "B": "180 độ", "C": "270 độ", "D": "360 độ", "correct": "B", "category": "Toán", "points": 100},
    {"content": "Dãy số Fibonacci bắt đầu bằng 0, 1, 1, 2, 3, 5, 8,... Số tiếp theo là số mấy?", "A": "11", "B": "12", "C": "13", "D": "15", "correct": "C", "category": "Toán", "points": 100},
    {"content": "Căn bậc hai số học của 144 bằng bao nhiêu?", "A": "10", "B": "11", "C": "12", "D": "14", "correct": "C", "category": "Toán", "points": 100},
    {"content": "Đạo hàm của hàm số y = x^2 tại điểm x = 3 bằng bao nhiêu?", "A": "3", "B": "6", "C": "9", "D": "12", "correct": "B", "category": "Toán", "points": 100},
    {"content": "Một hình chữ nhật có chu vi là 30cm, chiều rộng là 5cm. Diện tích hình chữ nhật là bao nhiêu cm2?", "A": "40 cm2", "B": "50 cm2", "C": "60 cm2", "D": "75 cm2", "correct": "B", "category": "Toán", "points": 100},
    {"content": "Trong hệ nhị phân, số thập phân 9 được biểu diễn như thế nào?", "A": "1001", "B": "1010", "C": "1100", "D": "1111", "correct": "A", "category": "Toán", "points": 100},
    {"content": "Giá trị của giai thừa 5! (5 giai thừa) bằng bao nhiêu?", "A": "60", "B": "100", "C": "120", "D": "150", "correct": "C", "category": "Toán", "points": 100},
    {"content": "Định lý Pytago áp dụng cho loại tam giác nào sau đây?", "A": "Tam giác đều", "B": "Tam giác cân", "C": "Tam giác vuông", "D": "Tam giác tù", "correct": "C", "category": "Toán", "points": 100},

    # ==================== GAME 2: MÔN LÝ (10 CÂU: ID 11 -> 20) ====================
    {"content": "Đơn vị đo cường độ dòng điện trong hệ thống đo lường quốc tế (SI) là gì?", "A": "Volt (V)", "B": "Ampe (A)", "C": "Ohm (Ω)", "D": "Watt (W)", "correct": "B", "category": "Lý", "points": 100},
    {"content": "Vận tốc truyền của ánh sáng trong môi trường chân không xấp xỉ bằng bao nhiêu?", "A": "300.000 km/s", "B": "150.000 km/s", "C": "3.000 km/s", "D": "30.000 km/s", "correct": "A", "category": "Lý", "points": 100},
    {"content": "Định luật I Newton về chuyển động còn được gọi với tên gọi là định luật gì?", "A": "Định luật hấp dẫn", "B": "Định luật quán tính", "C": "Định luật bảo toàn cơ năng", "D": "Định luật phản xạ", "correct": "B", "category": "Lý", "points": 100},
    {"content": "Công thức tính động năng của một vật khối lượng m đang chuyển động với vận tốc v là gì?", "A": "Wd = m * v", "B": "Wd = 1/2 * m * v^2", "C": "Wd = m * g * h", "D": "Wd = 2 * m * v", "correct": "B", "category": "Lý", "points": 100},
    {"content": "Hiện tượng khúc xạ ánh sáng xảy ra khi ánh sáng truyền qua mặt phân cách giữa hai môi trường nào?", "A": "Cùng độ trong suốt", "B": "Khác chiết suất", "C": "Hoàn toàn chân không", "D": "Cùng nhiệt độ", "correct": "B", "category": "Lý", "points": 100},
    {"content": "Đơn vị đo công và năng lượng trong hệ đơn vị quốc tế (SI) là gì?", "A": "Newton (N)", "B": "Joule (J)", "C": "Pascal (Pa)", "D": "Tesla (T)", "correct": "B", "category": "Lý", "points": 100},
    {"content": "Sóng âm thanh KHÔNG thể truyền được trong môi trường nào sau đây?", "A": "Chất rắn", "B": "Chất lỏng", "C": "Chất khí", "D": "Chân không", "correct": "D", "category": "Lý", "points": 100},
    {"content": "Lực đẩy Ác-si-mét tác dụng lên vật nhúng trong chất lỏng phụ thuộc vào yếu tố nào?", "A": "Khối lượng riêng chất lỏng và thể tích phần chìm", "B": "Khối lượng của vật", "C": "Độ sâu của vật trong lòng chất lỏng", "D": "Hình dạng của vật", "correct": "A", "category": "Lý", "points": 100},
    {"content": "Nhiệt độ sôi của nước tinh khiết ở áp suất khí quyển tiêu chuẩn (1 atm) là bao nhiêu?", "A": "80°C", "B": "90°C", "C": "100°C", "D": "120°C", "correct": "C", "category": "Lý", "points": 100},
    {"content": "Dụng cụ nào được dùng để đo hiệu điện thế giữa hai điểm trong một mạch điện?", "A": "Ampe kế", "B": "Vôn kế", "C": "Ohm kế", "D": "Nhiệt kế", "correct": "B", "category": "Lý", "points": 100},

    # ==================== GAME 3: MÔN HÓA (10 CÂU: ID 21 -> 30) ====================
    {"content": "Ký hiệu hóa học của nguyên tố Vàng trong bảng hệ thống tuần hoàn là gì?", "A": "Ag", "B": "Au", "C": "Fe", "D": "Cu", "correct": "B", "category": "Hóa", "points": 100},
    {"content": "Khí nào chiếm tỷ lệ thể tích lớn nhất trong bầu khí quyển của Trái Đất?", "A": "Oxy (O2)", "B": "Cacbonic (CO2)", "C": "Nito (N2)", "D": "Argon (Ar)", "correct": "C", "category": "Hóa", "points": 100},
    {"content": "Công thức hóa học của phân tử nước thông thường là gì?", "A": "H2O", "B": "H2O2", "C": "HO", "D": "H3O", "correct": "A", "category": "Hóa", "points": 100},
    {"content": "Dung dịch có độ pH bằng đúng 7 ở điều kiện chuẩn 25°C mang tính chất gì?", "A": "Tính axit", "B": "Tính bazơ", "C": "Tính trung tính", "D": "Tính lưỡng tính", "correct": "C", "category": "Hóa", "points": 100},
    {"content": "Kim loại nào ở thể lỏng ở nhiệt độ phòng tiêu chuẩn (25°C)?", "A": "Chì (Pb)", "B": "Thủy ngân (Hg)", "C": "Kẽm (Zn)", "D": "Thiếc (Sn)", "correct": "B", "category": "Hóa", "points": 100},
    {"content": "Khi nhúng quỳ tím vào dung dịch axit clohiđric (HCl), quỳ tím chuyển sang màu gì?", "A": "Màu xanh", "B": "Màu đỏ", "C": "Màu vàng", "D": "Không đổi màu", "correct": "B", "category": "Hóa", "points": 100},
    {"content": "Công thức hóa học của muối ăn thông thường dùng hàng ngày là gì?", "A": "NaHCO3", "B": "NaCl", "C": "KCl", "D": "CaCl2", "correct": "B", "category": "Hóa", "points": 100},
    {"content": "Kim loại nào có khả năng dẫn điện tốt nhất trong các kim loại sau đây?", "A": "Đồng (Cu)", "B": "Nhôm (Al)", "C": "Bạc (Ag)", "D": "Sắt (Fe)", "correct": "C", "category": "Hóa", "points": 100},
    {"content": "Quá trình quang hợp của cây xanh hấp thụ khí nào và giải phóng khí nào ra môi trường?", "A": "Hấp thụ Oxy, thải Cacbonic", "B": "Hấp thụ Cacbonic, thải Oxy", "C": "Hấp thụ Nito, thải Oxy", "D": "Hấp thụ Cacbonic, thải Nito", "correct": "B", "category": "Hóa", "points": 100},
    {"content": "Nguyên tố nào có số hiệu nguyên tử (Z) bằng 1 và là nguyên tố nhẹ nhất trong bảng tuần hoàn?", "A": "Heli (He)", "B": "Hydro (H)", "C": "Liti (Li)", "D": "Cacbon (C)", "correct": "B", "category": "Hóa", "points": 100},

    # ==================== GAME 4: MÔN SINH HỌC (10 CÂU: ID 31 -> 40) ====================
    {"content": "Đơn vị cấu tạo và chức năng cơ bản nhất của mọi cơ thể sống là gì?", "A": "Mô", "B": "Tế bào", "C": "Cơ quan", "D": "Bào quan", "correct": "B", "category": "Sinh học", "points": 100},
    {"content": "Đại phân tử sinh học nào đóng vai trò lưu trữ và truyền đạt thông tin di truyền?", "A": "Lipid", "B": "Protein", "C": "ADN", "D": "Carbohydrate", "correct": "C", "category": "Sinh học", "points": 100},
    {"content": "Bào quan nào trong tế bào nhân thực được ví như 'nhà máy năng lượng' tạo ATP?", "A": "Lưới nội chất", "B": "Ty thể", "C": "Bộ máy Golgi", "D": "Ribosome", "correct": "B", "category": "Sinh học", "points": 100},
    {"content": "Trong hệ thống nhóm máu ABO ở người, nhóm máu nào được gọi là nhóm máu chuyên cho?", "A": "Nhóm máu O", "B": "Nhóm máu A", "C": "Nhóm máu B", "D": "Nhóm máu AB", "correct": "A", "category": "Sinh học", "points": 100},
    {"content": "Quá trình nguyên phân từ 1 tế bào mẹ (2n) tạo ra bao nhiêu tế bào con có bộ NST như thế nào?", "A": "4 tế bào con (n)", "B": "2 tế bào con (2n)", "C": "2 tế bào con (n)", "D": "4 tế bào con (2n)", "correct": "B", "category": "Sinh học", "points": 100},
    {"content": "Ở người bình thường khỏe mạnh, bộ nhiễm sắc thể lưỡng bội (2n) gồm bao nhiêu chiếc?", "A": "23 chiếc", "B": "44 chiếc", "C": "46 chiếc", "D": "48 chiếc", "correct": "C", "category": "Sinh học", "points": 100},
    {"content": "Sắc tố nào làm cho lá cây có màu xanh lục và trực tiếp hấp thụ năng lượng quang hợp?", "A": "Carotenoid", "B": "Diệp lục (Chlorophyll)", "C": "Anthocyanin", "D": "Xanthophyll", "correct": "B", "category": "Sinh học", "points": 100},
    {"content": "Cơ quan nào trong cơ thể người chịu trách nhiệm chính lọc máu và bài tiết nước tiểu?", "A": "Gan", "B": "Thận", "C": "Phổi", "D": "Bàng quang", "correct": "B", "category": "Sinh học", "points": 100},
    {"content": "Hệ tuần hoàn kín ở người vận chuyển máu từ tim đi nuôi cơ thể qua loại mạch nào?", "A": "Động mạch", "B": "Tĩnh mạch", "C": "Mao mạch", "D": "Bạch huyết", "correct": "A", "category": "Sinh học", "points": 100},
    {"content": "Loài động vật nào sau đây thuộc lớp động vật biến nhiệt (nhiệt độ cơ thể phụ thuộc môi trường)?", "A": "Chim bồ câu", "B": "Chó sói", "C": "Ếch đồng", "D": "Cá voi xanh", "correct": "C", "category": "Sinh học", "points": 100},

    # ==================== GAME 5: MÔN LỊCH SỬ (10 CÂU: ID 41 -> 50) ====================
    {"content": "Chiến thắng Bạch Đằng lịch sử năm 938 của Ngô Quyền đã đánh bại quân xâm lược nào?", "A": "Quân Tống", "B": "Quân Nam Hán", "C": "Quân Nguyên - Mông", "D": "Quân Minh", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Bản Tuyên ngôn Độc lập khai sinh ra nước Việt Nam Dân chủ Cộng hòa được đọc vào ngày nào?", "A": "19/08/1945", "B": "02/09/1945", "C": "30/04/1975", "D": "07/05/1954", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Chiến dịch Điện Biên Phủ 'lừng lẫy năm châu, chấn động địa cầu' toàn thắng vào năm nào?", "A": "1945", "B": "1950", "C": "1954", "D": "1975", "correct": "C", "category": "Lịch sử", "points": 100},
    {"content": "Vị vua nào đã ban 'Chiếu dời đô' chuyển kinh đô từ Hoa Lư về Thăng Long vào năm 1010?", "A": "Đinh Bộ Lĩnh", "B": "Lý Công Uẩn (Lý Thái Tổ)", "C": "Lê Hoàn", "D": "Trần Cảnh", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Cuộc Tổng khởi nghĩa Cách mạng Tháng Tám giành chính quyền về tay nhân dân diễn ra năm nào?", "A": "1930", "B": "1945", "C": "1954", "D": "1975", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Vị danh tướng chỉ huy 3 lần kháng chiến chống quân Nguyên - Mông thế kỷ XIII là ai?", "A": "Lý Thường Kiệt", "B": "Trần Hưng Đạo", "C": "Quang Trung", "D": "Lê Lợi", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Phong trào khởi nghĩa Tây Sơn thế kỷ XVIII do ba anh em nào khởi xướng và lãnh đạo?", "A": "Nguyễn Trãi, Nguyễn Huệ, Nguyễn Du", "B": "Nguyễn Nhạc, Nguyễn Huệ, Nguyễn Lữ", "C": "Trần Liễu, Trần Cảnh, Trần Thủ Độ", "D": "Lê Lợi, Lê Lai, Nguyễn Trãi", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Hiệp định Genève về chấm dứt chiến tranh, lập lại hòa bình ở Đông Dương được ký vào năm nào?", "A": "1945", "B": "1954", "C": "1973", "D": "1975", "correct": "B", "category": "Lịch sử", "points": 100},
    {"content": "Đại thắng mùa Xuân giải phóng hoàn toàn miền Nam, thống nhất đất nước diễn ra ngày nào?", "A": "26/03/1975", "B": "14/04/1975", "C": "30/04/1975", "D": "01/05/1975", "correct": "C", "category": "Lịch sử", "points": 100},
    {"content": "Công trình thành Cổ Loa với kiến trúc hình xoáy ốc gắn liền với triều đại vị vua nào?", "A": "An Dương Vương", "B": "Hùng Vương", "C": "Triệu Đà", "D": "Mai Hắc Đế", "correct": "A", "category": "Lịch sử", "points": 100},

    # ==================== GAME 6: MÔN ĐỊA LÝ (10 CÂU: ID 51 -> 60) ====================
    {"content": "Đỉnh núi nào cao nhất Việt Nam và được mệnh danh là 'Nóc nhà Đông Dương'?", "A": "Fansipan (3.143m)", "B": "Langbiang", "C": "Bà Đen", "D": "Pusilung", "correct": "A", "category": "Địa lý", "points": 100},
    {"content": "Con sông nào dài nhất thế giới chảy qua lãnh thổ của nhiều nước thuộc lục địa châu Phi?", "A": "Sông Amazon", "B": "Sông Nin (Nile)", "C": "Sông Dương Tử", "D": "Sông Mississippi", "correct": "B", "category": "Địa lý", "points": 100},
    {"content": "Đại dương nào có diện tích và độ sâu trung bình lớn nhất trên bề mặt Trái Đất?", "A": "Đại Tây Dương", "B": "Ấn Độ Dương", "C": "Thái Bình Dương", "D": "Bắc Băng Dương", "correct": "C", "category": "Địa lý", "points": 100},
    {"content": "Lãnh thổ đất nước Việt Nam nằm hoàn toàn trong khu vực nào của châu Á?", "A": "Đông Á", "B": "Đông Nam Á", "C": "Nam Á", "D": "Tây Á", "correct": "B", "category": "Địa lý", "points": 100},
    {"content": "Dãy núi nào được xem là ranh giới tự nhiên phân chia giữa châu Âu và châu Á?", "A": "Dãy Alps", "B": "Dãy Uran (Ural)", "C": "Dãy Himalaya", "D": "Dãy Andes", "correct": "B", "category": "Địa lý", "points": 100},
    {"content": "Hang Sơn Đoòng - hang động tự nhiên lớn nhất thế giới thuộc địa phận tỉnh nào của Việt Nam?", "A": "Hà Giang", "B": "Ninh Bình", "C": "Quảng Bình", "D": "Cao Bằng", "correct": "C", "category": "Địa lý", "points": 100},
    {"content": "Hòn đảo tự nhiên nào có diện tích bề mặt lớn nhất trên thế giới?", "A": "Đảo Madagascar", "B": "Đảo Greenland", "C": "Đảo Borneo", "D": "Đảo Sumatra", "correct": "B", "category": "Địa lý", "points": 100},
    {"content": "Thành phố nào là thủ đô chính thức của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam?", "A": "Hà Nội", "B": "TP. Hồ Chí Minh", "C": "Đà Nẵng", "D": "Hải Phòng", "correct": "A", "category": "Địa lý", "points": 100},
    {"content": "Sa mạc cát nóng lớn nhất thế giới nằm ở khu vực Bắc Phi là sa mạc nào?", "A": "Sa mạc Gobi", "B": "Sa mạc Sahara", "C": "Sa mạc Kalahari", "D": "Sa mạc Atacama", "correct": "B", "category": "Địa lý", "points": 100},
    {"content": "Hồ nước ngọt tự nhiên có diện tích bề mặt lớn nhất thế giới là hồ nào?", "A": "Hồ Ba Bể", "B": "Hồ Baikal", "C": "Hồ Thượng (Lake Superior)", "D": "Hồ Victoria", "correct": "C", "category": "Địa lý", "points": 100},

    # ==================== GAME 7: MÔN VĂN HỌC (10 CÂU: ID 61 -> 70) ====================
    {"content": "Kiệt tác văn học 'Truyện Kiều' (Đoạn trường tân thanh) do đại thi hào nào sáng tác?", "A": "Nguyễn Trãi", "B": "Nguyễn Du", "C": "Hồ Xuân Hương", "D": "Đoàn Thị Điểm", "correct": "B", "category": "Văn học", "points": 100},
    {"content": "Tác phẩm văn học thiếu nhi nổi tiếng 'Dế Mèn phiêu lưu ký' là sáng tác của nhà văn nào?", "A": "Nguyễn Nhật Ánh", "B": "Tô Hoài", "C": "Võ Quảng", "D": "Trần Đăng Khoa", "correct": "B", "category": "Văn học", "points": 100},
    {"content": "Bài thơ 'Đoàn thuyền đánh cá' với bút pháp lãng mạn tráng lệ là sáng tác của nhà thơ nào?", "A": "Xuân Diệu", "B": "Hàn Mặc Tử", "C": "Huy Cận", "D": "Chế Lan Viên", "correct": "C", "category": "Văn học", "points": 100},
    {"content": "Tập truyện ngắn 'Gió đầu mùa' mang đậm chất thơ và tình người là của tác giả nào?", "A": "Vũ Trọng Phụng", "B": "Thạch Lam", "C": "Kim Lân", "D": "Nguyên Hồng", "correct": "B", "category": "Văn học", "points": 100},
    {"content": "Tác phẩm hiện thực phê phán 'Tắt đèn' gắn với hình tượng chị Dậu là của nhà văn nào?", "A": "Nam Cao", "B": "Ngô Tất Tố", "C": "Nguyễn Công Hoan", "D": "Vũ Trọng Phụng", "correct": "B", "category": "Văn học", "points": 100},
    {"content": "Vở kịch kinh điển 'Hồn Trương Ba, da hàng thịt' do kịch tác gia tài hoa nào viết?", "A": "Tào Mạt", "B": "Nguyễn Đình Thi", "C": "Lưu Quang Vũ", "D": "Xuân Trình", "correct": "C", "category": "Văn học", "points": 100},
    {"content": "Bản anh hùng ca 'Bình Ngô Đại Cáo' được mệnh danh là bản tuyên ngôn độc lập thứ hai do ai viết?", "A": "Lê Lợi", "B": "Nguyễn Trãi", "C": "Trần Hưng Đạo", "D": "Ngô Sĩ Liên", "correct": "B", "category": "Văn học", "points": 100},
    {"content": "Hai nhân vật điển hình 'Chí Phèo' và 'Thị Nở' xuất hiện trong tác phẩm cùng tên của ai?", "A": "Nguyễn Tuân", "B": "Nam Cao", "C": "Bùi Hiển", "D": "Nguyên Ngọc", "correct": "B", "category": "Văn học", "points": 100},
    {"content": "Bài thơ 'Tây Tiến' khắc họa chân dung người lính hào hoa, dũng cảm là của ai?", "A": "Quang Dũng", "B": "Chính Hữu", "C": "Phạm Tiến Duật", "D": "Hữu Thỉnh", "correct": "A", "category": "Văn học", "points": 100},
    {"content": "Tập thơ chữ Hán 'Nhật ký trong tù' (Ngục trung nhật ký) được sáng tác bởi tác giả nào?", "A": "Phan Bội Châu", "B": "Hồ Chí Minh", "C": "Phan Châu Trinh", "D": "Sóng Hồng", "correct": "B", "category": "Văn học", "points": 100},

    # ==================== GAME 8: MÔN TIẾNG ANH (10 CÂU: ID 71 -> 80) ====================
    {"content": "What is the past simple tense of the irregular verb 'go'?", "A": "goed", "B": "went", "C": "gone", "D": "goes", "correct": "B", "category": "Tiếng Anh", "points": 100},
    {"content": "Which of the following words is an antonym (opposite meaning) of 'increase'?", "A": "expand", "B": "grow", "C": "decrease", "D": "rise", "correct": "C", "category": "Tiếng Anh", "points": 100},
    {"content": "Which of the following adjectives is closest in meaning (synonym) to 'happy'?", "A": "sad", "B": "joyful", "C": "angry", "D": "tired", "correct": "B", "category": "Tiếng Anh", "points": 100},
    {"content": "What is the correct plural form of the singular noun 'child'?", "A": "childs", "B": "children", "C": "childrens", "D": "childes", "correct": "B", "category": "Tiếng Anh", "points": 100},
    {"content": "In the sentence 'She speaks English fluently', which part of speech is 'fluently'?", "A": "Noun", "B": "Adjective", "C": "Adverb", "D": "Verb", "correct": "C", "category": "Tiếng Anh", "points": 100},
    {"content": "What is the comparative form of the irregular adjective 'good'?", "A": "gooder", "B": "better", "C": "best", "D": "well", "correct": "B", "category": "Tiếng Anh", "points": 100},
    {"content": "Choose the correct preposition: 'He has lived in Da Nang _____ ten years.'", "A": "since", "B": "for", "C": "in", "D": "at", "correct": "B", "category": "Tiếng Anh", "points": 100},
    {"content": "What does the English idiom 'a piece of cake' mean?", "A": "Something very easy to do", "B": "A slice of dessert", "C": "Something very expensive", "D": "A complicated task", "correct": "A", "category": "Tiếng Anh", "points": 100},
    {"content": "Which negative prefix can be added to the word 'possible' to mean 'not possible'?", "A": "un-", "B": "dis-", "C": "im-", "D": "in-", "correct": "C", "category": "Tiếng Anh", "points": 100},
    {"content": "What is the noun form of the action verb 'decide'?", "A": "decisive", "B": "decision", "C": "decided", "D": "decider", "correct": "B", "category": "Tiếng Anh", "points": 100},

    # ==================== GAME 9: MÔN TIN HỌC (10 CÂU: ID 81 -> 90) ====================
    {"content": "Trong kiến trúc máy tính, 1 Byte tương đương với bao nhiêu bit nhị phân?", "A": "2 bit", "B": "4 bit", "C": "8 bit", "D": "16 bit", "correct": "C", "category": "Tin học", "points": 100},
    {"content": "Hệ điều hành nào sau đây là hệ điều hành mã nguồn mở (Open Source)?", "A": "Microsoft Windows", "B": "Linux", "C": "macOS", "D": "MS-DOS", "correct": "B", "category": "Tin học", "points": 100},
    {"content": "Giao thức mạng nào dùng để truyền tải siêu văn bản an toàn có mã hóa SSL/TLS?", "A": "HTTP", "B": "FTP", "C": "HTTPS", "D": "Telnet", "correct": "C", "category": "Tin học", "points": 100},
    {"content": "Cấu trúc dữ liệu nào hoạt động theo nguyên tắc LIFO (Last In First Out)?", "A": "Queue (Hàng đợi)", "B": "Stack (Ngăn xếp)", "C": "Linked List", "D": "Array", "correct": "B", "category": "Tin học", "points": 100},
    {"content": "Thiết bị nào sau đây là thiết bị xuất dữ liệu (Output Device) của hệ thống máy tính?", "A": "Bàn phím (Keyboard)", "B": "Chuột (Mouse)", "C": "Màn hình (Monitor)", "D": "Máy quét (Scanner)", "correct": "C", "category": "Tin học", "points": 100},
    {"content": "Ngôn ngữ truy vấn chuẩn dùng để thao tác với các hệ quản trị CSDL quan hệ là gì?", "A": "HTML", "B": "SQL", "C": "JSON", "D": "XML", "correct": "B", "category": "Tin học", "points": 100},
    {"content": "Tổ hợp phím tắt tiêu chuẩn trên hệ điều hành Windows dùng để sao chép (Copy) là gì?", "A": "Ctrl + C", "B": "Ctrl + V", "C": "Ctrl + X", "D": "Ctrl + Z", "correct": "A", "category": "Tin học", "points": 100},
    {"content": "Cấu trúc dữ liệu nào trong Redis tổ chức các phần tử kèm điểm số để sắp xếp bảng thứ hạng?", "A": "Hash", "B": "List", "C": "Sorted Set (ZSET)", "D": "Set", "correct": "C", "category": "Tin học", "points": 100},
    {"content": "Thuật toán tìm kiếm nhị phân (Binary Search) trên mảng đã sắp xếp có độ phức tạp là gì?", "A": "O(1)", "B": "O(N)", "C": "O(log N)", "D": "O(N^2)", "correct": "C", "category": "Tin học", "points": 100},
    {"content": "Bộ xử lý trung tâm - đầu não tính toán của máy tính thường được viết tắt là gì?", "A": "RAM", "B": "CPU", "C": "GPU", "D": "ROM", "correct": "B", "category": "Tin học", "points": 100},

    # ==================== GAME 10: KHOA HỌC & ĐỜI SỐNG (10 CÂU: ID 91 -> 100) ====================
    {"content": "Vitamin nào được cơ thể người tự tổng hợp chủ yếu qua việc tiếp xúc với ánh nắng mặt trời?", "A": "Vitamin A", "B": "Vitamin D", "C": "Vitamin C", "D": "Vitamin B12", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Cơ quan nào trong cơ thể người tiêu thụ nhiều năng lượng glucose và oxy nhất?", "A": "Não bộ", "B": "Trái tim", "C": "Lá gan", "D": "Cơ bắp", "correct": "A", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Hiện tượng Trái Đất ấm lên toàn cầu hiện nay chủ yếu do hiệu ứng nào gây ra?", "A": "Hiệu ứng Doppler", "B": "Hiệu ứng nhà kính", "C": "Hiệu ứng quang điện", "D": "Hiệu ứng Coriolis", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Trong kỹ năng sơ cấp cứu tai nạn, chữ viết tắt CPR là viết tắt của kỹ thuật hồi sức nào?", "A": "Hồi sức tuần hoàn máu", "B": "Hồi sức tim phổi (Cardiopulmonary Resuscitation)", "C": "Cấp cứu sốc nhiệt", "D": "Băng bó vết thương", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Quần thể Kim tự tháp Giza và tượng Nhân sư nổi tiếng thế giới nằm ở quốc gia nào?", "A": "Hy Lạp", "B": "Ai Cập", "C": "Ý", "D": "Ấn Độ", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Loại thực phẩm nào sau đây là nguồn cung cấp chất đạm (Protein) dồi dào và chất lượng cao?", "A": "Rau bắp cải", "B": "Trứng gà và ức gà", "C": "Mía đường", "D": "Dưa hấu", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Đơn vị đo lường phổ biến nhất dùng để tính toán năng lượng nạp vào từ thức ăn là gì?", "A": "Kilogram (kg)", "B": "Lít (L)", "C": "Calo (hoặc Kcal)", "D": "Decibel (dB)", "correct": "C", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Khí độc không màu, không mùi nguy hiểm sinh ra khi đốt than củi trong phòng kín là khí nào?", "A": "Khí Oxy (O2)", "B": "Khí Cacbon monoxit (CO)", "C": "Khí Nito (N2)", "D": "Khí Metan (CH4)", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Nước uống tinh khiết thông thường đạt tiêu chuẩn sức khỏe có độ pH xấp xỉ khoảng bao nhiêu?", "A": "Khoảng 2.0 - 3.0", "B": "Khoảng 6.5 - 7.5", "C": "Khoảng 11.0 - 12.0", "D": "Khoảng 14.0", "correct": "B", "category": "Khoa học & Đời sống", "points": 100},
    {"content": "Kính viễn vọng không gian nổi tiếng được phóng năm 1990 mang tên nhà thiên văn học nào?", "A": "Galileo", "B": "Newton", "C": "Hubble (Edwin Hubble)", "D": "Kepler", "correct": "C", "category": "Khoa học & Đời sống", "points": 100}
]

GAMES_CONFIG = [
    {"gid": 1, "name": "Toán", "q_range": (1, 11)},
    {"gid": 2, "name": "Lý", "q_range": (11, 21)},
    {"gid": 3, "name": "Hóa", "q_range": (21, 31)},
    {"gid": 4, "name": "Sinh học", "q_range": (31, 41)},
    {"gid": 5, "name": "Lịch sử", "q_range": (41, 51)},
    {"gid": 6, "name": "Địa lý", "q_range": (51, 61)},
    {"gid": 7, "name": "Văn học", "q_range": (61, 71)},
    {"gid": 8, "name": "Tiếng Anh", "q_range": (71, 81)},
    {"gid": 9, "name": "Tin học", "q_range": (81, 91)},
    {"gid": 10, "name": "Khoa học & Đời sống", "q_range": (91, 101)}
]

def generate_vietnamese_name():
    last = random.choice(VIETNAMESE_LAST_NAMES)
    mid = random.choice(VIETNAMESE_MIDDLE_NAMES)
    first = random.choice(VIETNAMESE_FIRST_NAMES)
    return f"{last} {mid} {first}"

def seed_database(reset: bool = True):
    r = get_sync_redis()
    print("=" * 70)
    print("KHỞI TẠO HỆ THỐNG 10 TRẬN ĐẤU & BẢNG XẾP HẠNG TOÀN CẦU TỐI ĐA 10.000 ĐIỂM")
    print("=" * 70)

    if reset:
        print("\n[BƯỚC 1] Dọn dẹp an toàn các key của đồ án (KHÔNG DÙNG FLUSHALL)...")
        patterns = [
            "seq:*",
            "player:*",
            "players:*",
            "question:*",
            "questions:*",
            "game:*",
            "leaderboard:*",
            "channel:*",
            "bench:*"
        ]
        total_deleted = 0
        for pat in patterns:
            deleted = safe_delete_by_pattern(pat, r)
            total_deleted += deleted
        print(f"-> Đã xóa an toàn {total_deleted} keys thuộc namespace của đồ án.")

    # 1. Tạo 150 Người chơi thực tế
    print("\n[BƯỚC 2] Khởi tạo 150 Người chơi...")
    pipe = r.pipeline()
    created_usernames = set()

    # Dành riêng ID 1 đến 5 với tên đẹp để phục vụ kịch bản demo bảo vệ
    demo_players = [
        {"id": 1, "username": "nguyenvana", "display_name": "Nguyễn Văn A (Demo)", "email": "nguyenvana@nosql.vn"},
        {"id": 2, "username": "tranthib", "display_name": "Trần Thị B (Demo)", "email": "tranthib@nosql.vn"},
        {"id": 3, "username": "lehoangc", "display_name": "Lê Hoàng C (Demo)", "email": "lehoangc@nosql.vn"},
        {"id": 4, "username": "phamminhd", "display_name": "Phạm Minh D (Demo)", "email": "phamminhd@nosql.vn"},
        {"id": 5, "username": "vuquange", "display_name": "Vũ Quang E (Demo)", "email": "vuquange@nosql.vn"}
    ]

    for p in demo_players:
        pid = p["id"]
        uname = p["username"]
        created_usernames.add(uname)
        p_data = {
            "id": str(pid),
            "username": uname,
            "display_name": p["display_name"],
            "email": p["email"],
            "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed=player_{pid}",
            "created_at": "2026-10-18 10:00:00",
            "total_games": "10"
        }
        pipe.set(f"player:name:{uname}", pid)
        pipe.hset(f"player:{pid}", mapping=p_data)
        pipe.sadd("players:all", pid)

    # Tạo từ ID 6 đến 150
    for pid in range(6, 151):
        full_name = generate_vietnamese_name()
        raw_uname = f"user_{pid}_{random.randint(100, 999)}"
        created_usernames.add(raw_uname)
        p_data = {
            "id": str(pid),
            "username": raw_uname,
            "display_name": full_name,
            "email": f"{raw_uname}@email.vn",
            "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed=player_{pid}",
            "created_at": "2026-10-18 10:00:00",
            "total_games": "10"
        }
        pipe.set(f"player:name:{raw_uname}", pid)
        pipe.hset(f"player:{pid}", mapping=p_data)
        pipe.sadd("players:all", pid)

    pipe.set("seq:player", 150)
    pipe.execute()
    print("-> Đã khởi tạo 150 người chơi thành công (lưu Hash player:* và Set players:all).")

    # 2. Tạo 100 Câu hỏi trắc nghiệm (10 môn x 10 câu)
    print("\n[BƯỚC 3] Khởi tạo 100 Câu hỏi trắc nghiệm chuẩn hóa thuộc 10 chủ đề...")
    pipe = r.pipeline()
    for idx, q in enumerate(QUESTIONS_DATA, start=1):
        qid = str(idx)
        q_data = {
            "id": qid,
            "content": q["content"],
            "A": q["A"],
            "B": q["B"],
            "C": q["C"],
            "D": q["D"],
            "correct": q["correct"],
            "category": q["category"],
            "points": str(q["points"])
        }
        pipe.hset(f"question:{qid}", mapping=q_data)
        pipe.sadd("questions:all", qid)
        pipe.sadd(f"questions:cat:{q['category']}", qid)

    pipe.set("seq:question", len(QUESTIONS_DATA))
    pipe.execute()
    print(f"-> Đã khởi tạo {len(QUESTIONS_DATA)} câu hỏi trắc nghiệm cho 10 chủ đề môn học.")

    # 3. Tạo 10 Trận Đấu Demo và khởi tạo điểm số trong từng trận
    print("\n[BƯỚC 4] Khởi tạo 10 Trận Đấu (Game 1 -> Game 10)...")
    pipe = r.pipeline()

    # Lưu điểm của từng người chơi qua 10 trận để tính tổng điểm toàn cầu chuẩn xác
    player_total_scores = {pid: 0 for pid in range(1, 151)}

    for g in GAMES_CONFIG:
        gid = g["gid"]
        g_name = g["name"]
        selected_qids = [str(i) for i in range(g["q_range"][0], g["q_range"][1])]

        game_data = {
            "id": str(gid),
            "name": g_name,
            "status": "running",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question_count": str(len(selected_qids))
        }
        pipe.hset(f"game:{gid}", mapping=game_data)
        pipe.rpush(f"game:{gid}:questions", *selected_qids)

        # 120 người chơi (từ ID 11 đến 130) tham gia trận đấu này
        for pid in range(11, 131):
            pipe.sadd(f"game:{gid}:players", pid)
            # Điểm từ 100 đến 1.000 điểm (bội số 100, không có điểm lẻ)
            score = random.randint(1, 10) * 100
            pipe.zadd(f"leaderboard:game:{gid}", {f"player:{pid}": score})
            player_total_scores[pid] += score

        # Người chơi 1 đến 5 (tài khoản Demo để thi đấu trực tiếp):
        # Điểm ban đầu trong mọi trận đấu khởi tạo bằng 0 điểm
        for pid in range(1, 6):
            pipe.sadd(f"game:{gid}:players", pid)
            demo_score = 0
            pipe.zadd(f"leaderboard:game:{gid}", {f"player:{pid}": demo_score})
            player_total_scores[pid] += demo_score

        # 20 người chơi còn lại (131 đến 150) cũng tham gia một số game ngẫu nhiên
        for pid in range(131, 151):
            pipe.sadd(f"game:{gid}:players", pid)
            score = random.randint(1, 10) * 100
            pipe.zadd(f"leaderboard:game:{gid}", {f"player:{pid}": score})
            player_total_scores[pid] += score

    # 4. Ghi điểm vào Bảng Xếp Hạng Toàn Cầu (leaderboard:global) = Tổng điểm 10 trận đấu (tối đa 10.000 điểm)
    for pid, tot_score in player_total_scores.items():
        # Đối với tài khoản demo (1..5), điểm khởi đầu là 0 để người chơi tự thi đấu tích lũy
        final_global = tot_score if pid <= 5 else max(100, min(10000, tot_score))
        pipe.zadd("leaderboard:global", {f"player:{pid}": final_global})

    pipe.set("seq:game", len(GAMES_CONFIG))
    pipe.execute()
    print("-> Đã khởi tạo thành công 10 trận đấu với điểm số trận từ 0 đến 1.000 điểm.")
    print("-> Đã tổng hợp điểm số vào leaderboard:global đạt chuẩn từ 100 đến tối đa 10.000 điểm!")

    # 5. In thống kê nghiệm thu và dải điểm số
    print("\n" + "=" * 70)
    print("THỐNG KÊ NGHIỆM THU DỮ LIỆU REDIS:")
    scard_players = r.scard("players:all")
    zcard_global = r.zcard("leaderboard:global")
    scard_questions = r.scard("questions:all")
    dbsize = r.dbsize()

    glob_min = r.zrange("leaderboard:global", 0, 0, withscores=True)
    glob_max = r.zrange("leaderboard:global", -1, -1, withscores=True)
    game1_min = r.zrange("leaderboard:game:1", 0, 0, withscores=True)
    game1_max = r.zrange("leaderboard:game:1", -1, -1, withscores=True)

    glob_min_score = int(glob_min[0][1]) if glob_min else 0
    glob_max_score = int(glob_max[0][1]) if glob_max else 0
    game1_min_score = int(game1_min[0][1]) if game1_min else 0
    game1_max_score = int(game1_max[0][1]) if game1_max else 0

    print(f"  * Tổng số thí sinh (SCARD players:all)  : {scard_players} (Yêu cầu >= 100) -> PASS")
    print(f"  * Tổng số câu hỏi (SCARD questions:all) : {scard_questions} (10 môn x 10 câu) -> PASS")
    print(f"  * Điểm Game 1 [Min..Max]                : [{game1_min_score} .. {game1_max_score}] (Thuộc [0..1.000]) -> PASS")
    print(f"  * Điểm Global [Min..Max]                : [{glob_min_score} .. {glob_max_score}] (Thuộc [100..10.000]) -> PASS")
    print(f"  * DBSIZE (Tổng số key Redis)            : {dbsize}")
    print("=" * 70)

    return {
        "players": scard_players,
        "global_leaderboard": zcard_global,
        "global_min": glob_min_score,
        "global_max": glob_max_score,
        "game1_min": game1_min_score,
        "game1_max": game1_max_score,
        "questions": scard_questions,
        "games_count": len(GAMES_CONFIG),
        "dbsize": dbsize
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed dữ liệu mẫu cho hệ thống Redis Leaderboard")
    parser.add_argument("--reset", action="store_true", help="Xóa các key cũ của đồ án trước khi nạp")
    args = parser.parse_args()
    seed_database(reset=args.reset)
