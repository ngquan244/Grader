"""
Application constants
"""
from enum import Enum


class Role(str, Enum):
    """User roles"""
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"


class MessageRole(str, Enum):
    """Chat message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FileType(str, Enum):
    """Supported file types"""
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "xlsx"


class ScoreEvaluation(str, Enum):
    """Score evaluation categories"""
    EXCELLENT = "Xuất sắc"
    GOOD = "Tốt"
    PASS = "Đạt"
    FAIL = "Chưa đạt"


# API Response Messages
class Messages:
    """API response messages"""
    
    # Success messages
    UPLOAD_SUCCESS = "Upload thành công"
    PDF_UPLOAD_SUCCESS = "Đã upload PDF đề thi thành công"
    IMAGE_UPLOAD_SUCCESS = "Đã upload ảnh thành công"
    QUIZ_CREATED = "Đã tạo quiz thành công"
    ROLE_SWITCHED = "Đã chuyển vai trò thành công"
    GRADING_COMPLETE = "Đã chấm điểm xong"
    HISTORY_CLEARED = "Đã xóa lịch sử chat"
    
    # Error messages
    EMPTY_MESSAGE = "Vui lòng nhập tin nhắn"
    FILE_NOT_FOUND = "Không tìm thấy file"
    PDF_NOT_FOUND = "Không tìm thấy file PDF"
    NO_QUESTIONS_FOUND = "Không tìm thấy câu hỏi trong PDF"
    INVALID_FILE_TYPE = "Loại file không hợp lệ"
    QUIZ_GEN_NOT_INSTALLED = "Module quiz-gen chưa được cài đặt"
    NO_GRADING_RESULTS = "Chưa có kết quả chấm điểm"
    DATABASE_CONNECTION_ERROR = "Lỗi kết nối cơ sở dữ liệu"
    
    # Role messages
    TEACHER_ONLY = "Chỉ giáo viên mới có quyền thực hiện thao tác này"
    STUDENT_ONLY = "Chỉ sinh viên mới có quyền thực hiện thao tác này"


# File size limits (in bytes)
class FileLimits:
    """File size limits"""
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_PDF_SIZE = 50 * 1024 * 1024    # 50MB
    MAX_UPLOAD_COUNT = 50


# Score thresholds
class ScoreThresholds:
    """Score evaluation thresholds"""
    EXCELLENT = 8.5
    GOOD = 7.0
    PASS = 5.0
