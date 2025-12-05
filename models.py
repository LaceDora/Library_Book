"""models.py

Chứa các model SQLAlchemy cho ứng dụng thư viện:
 - User: thông tin người dùng (mật khẩu được lưu bằng hash). Lưu ý: đăng nhập bằng `student_staff_id`.
 - Book: thông tin sách (title, author, quantity, category, views_count,...).
 - Borrow: lịch sử mượn trả (snapshot book_title để giữ lịch sử khi sách bị xóa).
 - Audit: ghi log các hành động admin/user để theo dõi.

Hàm tiện ích:
 - remove_username_unique_constraint(): cố gắng xóa ràng buộc UNIQUE trên cột username (nếu tồn tại) — thao tác schema runtime, nên dùng migration nếu cần thay đổi chính thức.

Gợi ý: dùng Flask-Migrate/Alembic cho production thay vì gọi trực tiếp ALTER TABLE từ code.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


def remove_username_unique_constraint():
    """Remove unique constraint from username column if it exists.

    Nếu constraint không tồn tại thì ignore lỗi. Thao tác này thay đổi schema runtime và
    chỉ nên chạy một lần khi cần. Đoạn thực thi sử dụng ALTER TABLE; đã bao bọc trong try/except.
    """
    try:
        with db.engine.connect() as conn:
            # Thực tế trong attachments: conn.execute(db.text('ALTER TABLE user DROP INDEX uq_user_username'))
            # commit được gọi sau đó. Giữ nguyên hành vi.
            conn.execute(db.text('ALTER TABLE user DROP INDEX uq_user_username'))
            conn.commit()
    except Exception:
        # Constraint có thể không tồn tại — bỏ qua lỗi
        pass


class User(db.Model):
    """Model User

    Trường chính:
    - id
    - username: hiển thị (KHÔNG unique)
    - password_hash: lưu hash mật khẩu
    - is_admin: quyền admin
    - student_staff_id: MSSV/MSCB (unique): dùng để đăng nhập/đăng ký
    - role: student/lecturer/staff
    - avatar_url, email (unique), phone (unique)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)  # Bỏ unique=True để cho phép trùng tên
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    # new fields
    student_staff_id = db.Column(db.String(20), unique=True, nullable=False)  # MSSV/MSCB phải unique
    role = db.Column(db.String(20), nullable=False, default='student')  # student/lecturer/staff
    avatar_url = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(30), unique=True, nullable=True)
    # Trạng thái tài khoản: True = active (có thể đăng nhập), False = bị khoá
    is_active = db.Column(db.Boolean, default=True)
    # Trạng thái xác thực email: True = đã xác thực, False = chưa xác thực
    email_verified = db.Column(db.Boolean, default=False)
    # Trạng thái xác thực sđt: True = đã xác thực, False = chưa xác thực
    phone_verified = db.Column(db.Boolean, default=False)


class Book(db.Model):
    """Model Book

    Lưu trữ thông tin về sách. `views_count` dùng để hiển thị số lượt xem.
    
    Hai cột quantity:
    - quantity: tổng số sách nhập vào ban đầu (không đổi)
    - available_quantity: số sách còn lại có thể mượn (cập nhật khi mượn/trả)
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=1)  # Số lượng ban đầu (không đổi)
    available_quantity = db.Column(db.Integer, default=1)  # Số lượng còn lại (thay đổi)
    category = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    views_count = db.Column(db.Integer, default=0)  # Changed from view_count to views_count to match usage in app.py
    description = db.Column(db.Text, nullable=True)

class Borrow(db.Model):
    """Model Borrow: lưu lịch sử mượn trả của user

    Ghi chú: snapshot `book_title` tại thời điểm mượn để đảm bảo lịch sử còn nguyên vẹn nếu book record bị xóa.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    borrow_date = db.Column(db.DateTime)
    # snapshot the book title at borrow time so history isn't lost if book is deleted
    book_title = db.Column(db.String(150))
    return_date = db.Column(db.DateTime, nullable=True)
    return_condition = db.Column(db.String(20), nullable=True)  # good, damaged, lost
    return_notes = db.Column(db.Text, nullable=True)
    # User-initiated return request: user clicks "Yêu cầu trả sách" -> admin will confirm
    return_requested = db.Column(db.Boolean, default=False)
    return_requested_at = db.Column(db.DateTime, nullable=True)
    # Borrow approval system
    status = db.Column(db.String(20), nullable=False, default='approved')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    expected_return_date = db.Column(db.DateTime, nullable=True)


class Audit(db.Model):
    """Model Audit: ghi nhận các hoạt động quan trọng (admin/user)

    Fields bổ sung: actor_user_id, target ids, timestamp, details
    """
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    target_borrow_id = db.Column(db.Integer, db.ForeignKey('borrow.id'), nullable=True)
    target_book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    details = db.Column(db.Text)


class EmailVerification(db.Model):
    """Model EmailVerification: lưu trữ OTP code cho xác thực email khi đăng ký
    
    Fields:
    - email: email cần xác thực
    - otp_code: mã OTP 6 chữ số
    - created_at: thời gian tạo
    - expires_at: thời gian hết hạn (10 phút)
    - verified: đã xác thực hay chưa
    - attempts: số lần thử gửi lại OTP (rate limiting)
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=1)


class PhoneVerification(db.Model):
    """Model PhoneVerification: lưu trữ OTP code cho xác thực số điện thoại
    
    Fields:
    - phone: số điện thoại cần xác thực
    - otp_code: mã OTP 6 chữ số
    - created_at: thời gian tạo
    - expires_at: thời gian hết hạn (5 phút)
    - verified: đã xác thực hay chưa
    - attempts: số lần thử gửi lại OTP
    """
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(30), nullable=False, index=True)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=1)


class PasswordReset(db.Model):
    """Model PasswordReset: lưu trữ mã reset password
    
    Fields:
    - user_id: ID của user yêu cầu reset
    - reset_code: mã reset 6 chữ số
    - created_at: thời gian tạo
    - expires_at: thời gian hết hạn (15 phút)
    - used: đã sử dụng hay chưa
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reset_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)


class Notification(db.Model):
    """Model Notification: lưu thông báo cho user và admin
    
    Fields:
    - user_id: người nhận thông báo
    - message: nội dung thông báo
    - link: đường dẫn liên kết (optional)
    - is_read: trạng thái đã đọc
    - type: loại thông báo (info, success, warning, error)
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    type = db.Column(db.String(20), default='info')
