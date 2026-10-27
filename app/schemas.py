from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal

# --- SCHEMAS NGƯỜI CHƠI (PLAYER) ---
class PlayerCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập duy nhất")
    display_name: str = Field(..., min_length=2, max_length=100, description="Tên hiển thị")
    email: EmailStr = Field(..., description="Email người chơi")
    avatar: Optional[str] = Field("https://api.dicebear.com/7.x/bottts/svg?seed=player", description="URL avatar")

class PlayerUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None

class PlayerResponse(BaseModel):
    id: int
    username: str
    display_name: str
    email: str
    avatar: str
    created_at: str
    total_games: int = 0

# --- SCHEMAS NGÂN HÀNG CÂU HỎI & CHỦ ĐỀ (QUESTION & CATEGORY) ---
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Tên chủ đề câu hỏi")

class CategoryDetail(BaseModel):
    name: str
    count: int = 0

class QuestionCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Nội dung câu hỏi")
    A: str = Field(..., min_length=1, description="Phương án A")
    B: str = Field(..., min_length=1, description="Phương án B")
    C: str = Field(..., min_length=1, description="Phương án C")
    D: str = Field(..., min_length=1, description="Phương án D")
    correct: Literal["A", "B", "C", "D"] = Field(..., description="Đáp án đúng (A/B/C/D)")
    category: str = Field("Chung", description="Chủ đề câu hỏi")
    points: int = Field(100, ge=1, le=1000, description="Điểm thưởng khi trả lời đúng")

class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    A: Optional[str] = None
    B: Optional[str] = None
    C: Optional[str] = None
    D: Optional[str] = None
    correct: Optional[Literal["A", "B", "C", "D"]] = None
    category: Optional[str] = None
    points: Optional[int] = Field(None, ge=1, le=1000)

class QuestionResponse(BaseModel):
    """Schema đầy đủ cho Admin (có đáp án đúng)"""
    id: int
    content: str
    A: str
    B: str
    C: str
    D: str
    correct: str
    category: str
    points: int

class QuestionInGame(BaseModel):
    """Schema trả về cho thí sinh khi làm bài (TUYỆT ĐỐI KHÔNG CÓ TRƯỜNG correct)"""
    id: int
    content: str
    A: str
    B: str
    C: str
    D: str
    category: str
    points: int

# --- SCHEMAS LƯỢT CHƠI (GAME) ---
class GameCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Tên lượt chơi")
    question_count: int = Field(10, ge=1, le=50, description="Số lượng câu hỏi")
    category: Optional[str] = Field(None, description="Lọc theo chủ đề (None = ngẫu nhiên)")

class GameStatusUpdate(BaseModel):
    status: Literal["waiting", "running", "finished"] = Field(..., description="Trạng thái mới")

class GameResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: str
    question_count: int
    players_count: int = 0

# --- SCHEMAS NỘP BÀI & TRẢ LỜI ---
class AnswerSubmit(BaseModel):
    player_id: int
    question_id: int
    choice: Literal["A", "B", "C", "D"]

class AnswerResult(BaseModel):
    correct: bool
    points_earned: int
    new_score: int
    new_rank: int
    message: str

# --- SCHEMAS BẢNG XẾP HẠNG (LEADERBOARD) ---
class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    username: str
    display_name: str
    avatar: str
    score: int

class AroundMeResponse(BaseModel):
    player_rank: int
    player_score: int
    total_players: int
    entries: List[LeaderboardEntry]
