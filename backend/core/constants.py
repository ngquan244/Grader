"""
Application constants
"""
from enum import Enum


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


# API Response Messages
class Messages:
    """API response messages"""
    
    # Success messages
    UPLOAD_SUCCESS = "Upload thành công"
    ROLE_SWITCHED = "Đã chuyển vai trò thành công"
    HISTORY_CLEARED = "Đã xóa lịch sử chat"
    
    # Error messages
    EMPTY_MESSAGE = "Vui lòng nhập tin nhắn"
    FILE_NOT_FOUND = "Không tìm thấy file"
    INVALID_FILE_TYPE = "Loại file không hợp lệ"
    DATABASE_CONNECTION_ERROR = "Lỗi kết nối cơ sở dữ liệu"


# File size limits (in bytes)
class FileLimits:
    """File size limits"""
    MAX_PDF_SIZE = 50 * 1024 * 1024    # 50MB
    MAX_UPLOAD_COUNT = 50
