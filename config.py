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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Email configuration (Flask-Mail)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Email address
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # App password (not regular password)
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME')
# OTP expiry time in minutes
app.config['OTP_EXPIRY_MINUTES'] = int(os.getenv('OTP_EXPIRY_MINUTES', 10))
app.config['RESET_CODE_EXPIRY_MINUTES'] = int(os.getenv('RESET_CODE_EXPIRY_MINUTES', 15))
# Loan period in days
LOAN_PERIOD_DAYS = 14

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

    # URL encode password to handle special characters like @
    from urllib.parse import quote_plus
    encoded_password = quote_plus(MYSQL_PASSWORD)

    # SQLAlchemy connection string (use pymysql driver)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
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
LIBRARY_ADMIN_EMAIL = os.getenv('LIBRARY_ADMIN_EMAIL', 'quochuyphan2k5@gmail.com')
LIBRARY_ADMIN_PHONE = os.getenv('LIBRARY_ADMIN_PHONE', '0798281104')
# Google OAuth config (load from env; safe to leave empty in non-OAuth environments)
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
# reCAPTCHA keys (set these in your .env when you register a site in Google reCAPTCHA)
app.config['RECAPTCHA_SITE_KEY'] = os.getenv('RECAPTCHA_SITE_KEY')
app.config['RECAPTCHA_SECRET_KEY'] = os.getenv('RECAPTCHA_SECRET_KEY')
# Initialize database
db.init_app(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
