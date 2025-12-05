"""app.py

Mục đích:
 - Khởi tạo và cấu hình các phần runtime của Flask app (một số cấu hình có thể đặt trong config.py nhưng một vài cấu hình cụ thể vẫn đặt ở đây).
 - Đăng ký các blueprints của ứng dụng.
 - Khởi tạo cơ sở dữ liệu (db.create_all()) và gọi hàm migrate nhẹ để xóa ràng buộc unique trên username nếu cần.
 - Xử lý lỗi upload file quá lớn (RequestEntityTooLarge).

Ghi chú nhanh trên các phần chính:
 - Error handler cho RequestEntityTooLarge: flash message và redirect về request.url.
 - Trong block __main__: tạo secret_key và SESSION_COOKIE_NAME dựa trên port để tránh xung đột session khi chạy nhiều instance.
"""

from config import app
from models import db
from flask import request, flash, redirect, url_for
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from email_service import send_return_reminder_email
from werkzeug.exceptions import RequestEntityTooLarge

# Cấu hình giới hạn kích thước upload
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Xử lý lỗi kích thước file quá lớn
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash('File tải lên quá lớn. Giới hạn là 2MB.', 'danger')
    return redirect(request.url)

# Initialize Flask-Mail
from email_service import mail
mail.init_app(app)

# Initialize APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def check_overdue_books():
    """Kiểm tra và gửi email nhắc nhở cho các sách sắp đến hạn hoặc quá hạn."""
    with app.app_context():
        # Lấy ngày hiện tại
        today = datetime.now()
        # Lấy ngày mai (để nhắc trước 1 ngày)
        tomorrow = today + timedelta(days=1)
        
        # Tìm các lượt mượn chưa trả
        from models import Borrow, User, Book
        
        # 1. Nhắc trước 1 ngày
        upcoming_returns = db.session.query(Borrow, User, Book).join(User).join(Book).filter(
            Borrow.return_date >= tomorrow.replace(hour=0, minute=0, second=0),
            Borrow.return_date < tomorrow.replace(hour=23, minute=59, second=59),
            Borrow.return_date != None,
            Borrow.return_condition == None  # Chưa trả
        ).all()
        
        for borrow, user, book in upcoming_returns:
            if user.email:
                print(f"Sending reminder to {user.email} for book {book.title}")
                send_return_reminder_email(user.email, user.username, book.title, borrow.return_date)

# Lên lịch chạy mỗi ngày vào 8:00 sáng
scheduler.add_job(id='check_overdue_books', func=check_overdue_books, trigger='cron', hour=8, minute=0)

# Import blueprints
from routes.main import main as main_blueprint
from routes.auth import auth as auth_blueprint
from routes.book import book as book_blueprint
from routes.user import user as user_blueprint
from routes.admin import admin as admin_blueprint
from routes.chatbot import chatbot as chatbot_blueprint
from routes.google_oauth import google_bp as google_oauth_blueprint
from routes.notification import notification_bp

# Register blueprints with unique names and prefixes
app.register_blueprint(main_blueprint, name='main_bp')
app.register_blueprint(auth_blueprint, name='auth_bp', url_prefix='/auth')
app.register_blueprint(book_blueprint, name='book_bp', url_prefix='/book')
app.register_blueprint(user_blueprint, name='user_bp', url_prefix='/user')
app.register_blueprint(admin_blueprint, name='admin_bp', url_prefix='/admin')
app.register_blueprint(chatbot_blueprint, name='chatbot_bp')
app.register_blueprint(google_oauth_blueprint, name='google_oauth_bp')
app.register_blueprint(notification_bp, name='notification_bp', url_prefix='/notification')

# Khởi tạo available_quantity từ quantity nếu chưa có
with app.app_context():
    try:
        from models import Book
        from sqlalchemy.exc import ProgrammingError
        
        books_need_update = Book.query.filter(
            (Book.available_quantity.is_(None)) | (Book.available_quantity == 0)
        ).all()
        for book in books_need_update:
            if book.available_quantity is None or book.available_quantity == 0:
                book.available_quantity = book.quantity or 1
        if books_need_update:
            db.session.commit()
            print(f"✓ Initialized available_quantity for {len(books_need_update)} books")
    except Exception as e:
        print(f"⚠ Skipped available_quantity init (Tables might not exist yet): {e}")

if __name__ == '__main__':
    import sys
    import uuid
    import socket
    import os

    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't need to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
    
    # Prefer PORT from environment (Railway provides it). Fallback to CLI arg or 8000
    port = int(os.environ.get('PORT') or (int(sys.argv[1]) if len(sys.argv) > 1 else 8000))

    # Secret key: prefer SECRET_KEY env var in production, else fallback to per-instance value
    app.secret_key = os.environ.get('SECRET_KEY') or f'library_secret_key_{port}_{uuid.uuid4().hex}'
    
    print(f"\nRunning on:")
    print(f" * http://127.0.0.1:{port}/")
    print(f" * http://{get_ip()}:{port}/\n")
    
    # Set session cookie name riêng cho mỗi port
    app.config['SESSION_COOKIE_NAME'] = f'session_port_{port}'
    
    print(f'Starting server on port {port} with unique session configuration')
    # Do not force debug=True here. Use FLASK_DEBUG or environment to control debug mode.
    debug_mode = os.environ.get('FLASK_DEBUG', '0') in ('1', 'true', 'True')
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
