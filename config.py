"""config.py

Mục đích:
 - Tạo và cấu hình instance Flask `app`.
 - Định nghĩa các cài đặt session, upload, DB connection và helper `allowed_file`.

Ghi chú:
 - Cấu hình DATABASE hiện đang dùng MySQL connector string cứng; tốt hơn là dùng biến môi trường để bảo mật.
 
"""

import os
from flask import Flask
from models import db

# Create Flask app
app = Flask(__name__)

# Secret key config sẽ được set trong app.py

# Session config
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Upload configuration for avatars
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max

# File upload config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Prefer a generic DATABASE_URL (Postgres) when provided (e.g., ElephantSQL or Render)
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_URI')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # MySQL config (fallback for PlanetScale / Railway style env vars)
    MYSQL_HOST = os.getenv('MYSQLHOST') or os.getenv('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.getenv('MYSQLUSER') or os.getenv('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.getenv('MYSQLPASSWORD') or os.getenv('MYSQL_PASSWORD') or ''
    MYSQL_DB = os.getenv('MYSQLDATABASE') or os.getenv('MYSQL_DATABASE') or 'library_db'
    MYSQL_PORT = os.getenv('MYSQLPORT') or os.getenv('MYSQL_PORT') or '3306'

    # SQLAlchemy connection string (use pymysql driver)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )

# SQLAlchemy common config
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
    'pool_size': 5,
    'max_overflow': 10,
    'connect_args': {
        'connect_timeout': 10
    }
}

# Category mapping
CATEGORY_MAP = {
    'am_nhac': 'Âm nhạc',
    'lap_trinh': 'Lập trình',
    'truyen_tranh': 'Truyện tranh',
    'y_hoc': 'Y học',
    'tam_ly': 'Tâm lý'
}

# Thông tin liên hệ thủ thư / admin (dùng cho trang Quên mật khẩu)
LIBRARY_ADMIN_EMAIL = os.getenv('LIBRARY_ADMIN_EMAIL', 'admin01@gmail.com')
LIBRARY_ADMIN_PHONE = os.getenv('LIBRARY_ADMIN_PHONE', '0798281104')
# Initialize database
db.init_app(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
