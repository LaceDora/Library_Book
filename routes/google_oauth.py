from flask import Blueprint, current_app, url_for, redirect, session, flash, render_template, request
from models import db, User
from authlib.integrations.flask_client import OAuth

google_bp = Blueprint('google_oauth', __name__)
oauth = OAuth()


@google_bp.record_once
def _init_oauth(state):
    # initialize oauth client with app config
    app = state.app
    oauth.init_app(app)
    # register google if not already registered
    if 'google' not in oauth._registry:
        oauth.register(
            name='google',
            client_id=app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )


@google_bp.route('/login/google')
def login_google():
    # redirect user to Google for authentication
    # Depending on how the blueprint was registered the endpoint prefix
    # may be 'google_oauth' or 'google_oauth_bp'. Try the registered name first.
    try:
        redirect_uri = url_for('google_oauth_bp.authorize', _external=True)
    except Exception:
        redirect_uri = url_for('google_oauth.authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@google_bp.route('/auth/callback')
def authorize():
    # callback endpoint that handles Google's response
    token = oauth.google.authorize_access_token()
    # Try to parse id_token first (OIDC), fallback to userinfo endpoint
    userinfo = None
    try:
        userinfo = oauth.google.parse_id_token(token)
    except Exception:
        pass
    if not userinfo:
        # Some registrations may not populate a base_url; call the full userinfo endpoint directly
        try:
            userinfo = oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo').json()
        except Exception:
            # fallback to older endpoint
            userinfo = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()

    # Tìm hoặc tạo user trong DB
    import hashlib
    email = userinfo.get('email')
    google_sub = userinfo.get('sub')
    name = userinfo.get('name') or (email.split('@')[0] if email else 'GoogleUser')

    # Derive a deterministic short student_staff_id from google_sub to fit column limit
    # Format: g_<sha1_prefix> where total length <= 20 (g_ + 17 hex = 19)
    sha = hashlib.sha1(google_sub.encode('utf-8')).hexdigest() if google_sub else None
    student_staff_id_for_google = f"g_{sha[:17]}" if sha else None

    # Tìm theo email trước; nếu không tìm thấy, tìm theo generated student_staff_id
    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    if not user and student_staff_id_for_google:
        user = User.query.filter_by(student_staff_id=student_staff_id_for_google).first()

    if not user:
        # User mới - lưu thông tin tạm vào session và chuyển đến trang setup
        session['google_setup'] = {
            'email': email,
            'name': name,
            'google_sub': google_sub,
            'student_staff_id': student_staff_id_for_google or f'google_{google_sub[:15]}'
        }
        return redirect(url_for('google_oauth_bp.setup_account'))
    else:
        # User đã tồn tại - đăng nhập luôn
        flash('Đăng nhập bằng Google thành công!', 'success')
        # Lưu vào session
        session['user_id'] = user.id
        session['email'] = user.email
        session['username'] = user.username
        session['role'] = user.role
        session['is_admin'] = user.is_admin
        session['google_sub'] = google_sub
        session['name'] = name
        return redirect(url_for('main_bp.index'))


@google_bp.route('/setup')
def setup_account():
    """Hiển thị trang setup cho user mới từ Google OAuth"""
    if 'google_setup' not in session:
        flash('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.', 'warning')
        return redirect(url_for('auth_bp.login'))
    
    setup_data = session['google_setup']
    return render_template('auth/google_setup.html', 
                         email=setup_data.get('email'),
                         name=setup_data.get('name'))


@google_bp.route('/complete-setup', methods=['POST'])
def complete_setup():
    """Xử lý form setup tài khoản từ Google OAuth"""
    if 'google_setup' not in session:
        flash('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.', 'warning')
        return redirect(url_for('auth_bp.login'))
    
    from werkzeug.security import generate_password_hash
    
    setup_data = session['google_setup']
    role = request.form.get('role')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate
    if not role or role not in ['student', 'lecturer', 'staff']:
        flash('Vui lòng chọn vai trò hợp lệ.', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
    
    if not password or len(password) < 6:
        flash('Mật khẩu phải có ít nhất 6 ký tự.', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
    
    # Validate password strength: must contain letter, number, and special character
    import re
    if not re.search(r'[A-Za-z]', password):
        flash('Mật khẩu phải chứa ít nhất một chữ cái.', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
    if not re.search(r'\d', password):
        flash('Mật khẩu phải chứa ít nhất một chữ số.', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
    if not re.search(r'[@$!%*#?&]', password):
        flash('Mật khẩu phải chứa ít nhất một ký tự đặc biệt (@$!%*#?&).', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
    
    if password != confirm_password:
        flash('Mật khẩu xác nhận không khớp.', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
    
    # Tạo user mới
    try:
        user = User(
            username=setup_data['name'],
            password_hash=generate_password_hash(password),
            student_staff_id=setup_data['student_staff_id'],
            role=role,
            email=setup_data['email'],
            is_active=True,
            email_verified=True  # Email từ Google đã verified
        )
        db.session.add(user)
        db.session.commit()
        
        # Xóa thông tin setup tạm
        session.pop('google_setup', None)
        
        # Đăng nhập luôn
        session['user_id'] = user.id
        session['email'] = user.email
        session['username'] = user.username
        session['role'] = user.role
        session['is_admin'] = user.is_admin
        session['google_sub'] = setup_data.get('google_sub')
        session['name'] = setup_data['name']
        
        flash('Đăng ký thành công! Chào mừng bạn đến với thư viện.', 'success')
        return redirect(url_for('main_bp.index'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi tạo tài khoản: {e}")
        flash('Có lỗi xảy ra khi tạo tài khoản. Vui lòng thử lại.', 'danger')
        return redirect(url_for('google_oauth_bp.setup_account'))
