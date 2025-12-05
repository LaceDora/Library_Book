"""routes/auth.py

Routes liên quan tới xác thực người dùng:
 - login: đăng nhập bằng `student_staff_id` (MSSV/MSCB) và password
 - logout: xóa session
 - register: tạo tài khoản mới (kiểm tra trùng MSSV/MSCB)

Ghi chú: `username` ở model là tên hiển thị, không dùng để đăng nhập (đăng nhập bằng student_staff_id).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import hashlib
import os
from config import LIBRARY_ADMIN_EMAIL, LIBRARY_ADMIN_PHONE
import re
import requests
from email_service import (
    create_email_verification, verify_otp_code, send_verification_email,
    create_password_reset, verify_reset_code, send_password_reset_email, mark_reset_code_used
)

auth = Blueprint('auth', __name__)

def hash_password(password):
    """Hash mật khẩu sử dụng SHA256 với salt."""
    salt = os.urandom(32)
    hash_obj = hashlib.sha256(salt + password.encode('utf-8'))
    return salt.hex() + hash_obj.hexdigest()

def verify_password(stored_password, provided_password):
    """Xác thực mật khẩu."""
    try:
        salt = bytes.fromhex(stored_password[:64])
        stored_hash = stored_password[64:]
        hash_obj = hashlib.sha256(salt + provided_password.encode('utf-8'))
        return hash_obj.hexdigest() == stored_hash
    except Exception:
        return False

def mask_email(email):
    """Mask email address for privacy (e.g., abc@gmail.com -> a**@gmail.com)."""
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked_local = local
    elif len(local) == 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 1)
    return f"{masked_local}@{domain}"

@auth.route("/login", methods=["GET", "POST"])
def login():
    """Xử lý POST/GET cho trang login.

    POST:
    - Lấy `login` field (MSSV/MSCB hoặc Email) và `password`.
    - Tìm user theo `student_staff_id` hoặc `email` và so sánh hash.
    - Nếu ok, lưu session và redirect.
    """
    if request.method == "POST":
        login_input = request.form["login"]  # Có thể là MSSV/MSCB hoặc Email
        password = request.form["password"]

        # If reCAPTCHA is configured, validate token before authenticating
        recaptcha_secret = current_app.config.get('RECAPTCHA_SECRET_KEY')
        if recaptcha_secret:
            recaptcha_response = request.form.get('g-recaptcha-response')
            if not recaptcha_response:
                flash('Vui lòng xác thực reCAPTCHA trước khi tiếp tục.', 'danger')
                return render_template('auth/login.html')
            try:
                verify = requests.post('https://www.google.com/recaptcha/api/siteverify', data={
                    'secret': recaptcha_secret,
                    'response': recaptcha_response,
                    'remoteip': request.remote_addr
                }, timeout=5)
                result = verify.json()
            except Exception:
                flash('Không thể xác thực reCAPTCHA. Vui lòng thử lại.', 'danger')
                return render_template('auth/login.html')
            if not result.get('success'):
                flash('Xác thực reCAPTCHA thất bại. Vui lòng thử lại.', 'danger')
                return render_template('auth/login.html')


        # Tìm user theo student_staff_id HOẶC email
        user = User.query.filter(
            (User.student_staff_id == login_input) | (User.email == login_input)
        ).first()

        if not user:
            flash("Sai MSSV/MSCB/Email hoặc mật khẩu!", "danger")
        elif not user.is_active:
            flash("Tài khoản này đã bị khoá. Liên hệ thủ thư để được hỗ trợ.", "danger")
        elif not user.email_verified:
            flash("Email chưa được xác thực. Vui lòng kiểm tra email để xác thực tài khoản.", "warning")
            return redirect(url_for('auth_bp.verify_email', email=user.email))
        elif verify_password(user.password_hash, password):
            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            session["username"] = user.username
            session["role"] = user.role
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for("main_bp.index"))
        else:
            # Mật khẩu sai
            flash("Sai MSSV/MSCB/Email hoặc mật khẩu!", "danger")
    return render_template("auth/login.html")

@auth.route("/logout")
def logout():
    """Xóa session và redirect về trang chủ."""
    session.clear()
    flash("Đã đăng xuất!", "info")
    return redirect(url_for("main_bp.index"))

@auth.route("/register", methods=["GET", "POST"])
def register():
    """Xử lý đăng ký tài khoản với xác thực email.

    POST:
    - Kiểm tra password/confirm
    - Kiểm tra email hợp lệ
    - Kiểm tra trùng `student_staff_id` và email
    - Tạo User với is_active=True, email_verified=False
    - Gửi OTP qua email
    """
    if request.method == "POST":
        username = request.form["username"]
        email = request.form.get("email", "").strip()
        password = request.form["password"]
        password_confirm = request.form["password_confirm"]
        student_staff_id = request.form["student_staff_id"]
        role = request.form.get("role", "student")
        
        # Prepare form data to pass back
        form_data = {
            'username': username,
            'email': email,
            'student_staff_id': student_staff_id,
            'role': role
        }

        # Validate email
        if not email or not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            flash("Email không hợp lệ!", "danger")
            return render_template("auth/register.html", **form_data)

        if password != password_confirm:
            flash("Mật khẩu xác nhận không khớp!", "danger")
            return render_template("auth/register.html", **form_data)

        # Kiểm tra độ mạnh mật khẩu với thông báo chi tiết
        def validate_password_strength(pw: str):
            """Validate password and return specific error messages."""
            if not pw or len(pw) < 6:
                return False, "Mật khẩu phải có ít nhất 6 ký tự"
            
            missing = []
            if not re.search(r'[A-Za-z]', pw):
                missing.append('chữ cái')
            if not re.search(r'\d', pw):
                missing.append('chữ số')
            if not re.search(r'[@$!%*#?&]', pw):
                missing.append('ký tự đặc biệt (@$!%*#?&)')
            
            if missing:
                return False, f"Mật khẩu thiếu: {', '.join(missing)}"
            
            return True, ""

        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, "danger")
            return render_template("auth/register.html", **form_data)

        # Kiểm tra trùng MSSV/MSCB
        if User.query.filter_by(student_staff_id=student_staff_id).first():
            flash("MSSV/MSCB này đã được đăng ký!", "danger")
            return render_template("auth/register.html", **form_data)
        
        # Kiểm tra trùng email
        if User.query.filter_by(email=email).first():
            flash("Email này đã được đăng ký!", "danger")
            return render_template("auth/register.html", **form_data)

        if role not in ["student", "staff", "lecturer"]:
            role = "student"

        # Tạo user với email_verified=False
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            student_staff_id=student_staff_id,
            role=role,
            is_active=True,
            email_verified=False
        )
        db.session.add(user)
        db.session.commit()

        # Tạo và gửi OTP
        otp_code, success, message = create_email_verification(email)
        print(f"[DEBUG] OTP Creation - Success: {success}, Message: {message}, Code: {otp_code}")
        if success:
            send_success, send_message = send_verification_email(email, otp_code)
            print(f"[DEBUG] Email Send - Success: {send_success}, Message: {send_message}")
            if send_success:
                flash("Đăng ký thành công! Vui lòng kiểm tra email để xác thực tài khoản.", "success")
                return redirect(url_for("auth_bp.verify_email", email=email))
            else:
                print(f"[ERROR] Failed to send email: {send_message}")
                flash(f"Đăng ký thành công nhưng không thể gửi email: {send_message}", "warning")
        else:
            print(f"[ERROR] Failed to create OTP: {message}")
            flash(f"Đăng ký thành công nhưng có lỗi: {message}", "warning")
        
        return redirect(url_for("auth_bp.verify_email", email=email))
    return render_template("auth/register.html")


@auth.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Trang xác thực email bằng OTP."""
    email = request.args.get('email') or request.form.get('email')
    
    if not email:
        flash('Email không hợp lệ.', 'danger')
        return redirect(url_for('auth_bp.register'))
    
    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()
        
        if not otp_code:
            flash('Vui lòng nhập mã OTP.', 'danger')
            return render_template('auth/verify_email.html', email=email)
        
        success, message = verify_otp_code(email, otp_code)
        if success:
            # Cập nhật email_verified cho user
            user = User.query.filter_by(email=email).first()
            if user:
                user.email_verified = True
                db.session.commit()
                flash('Xác thực email thành công!', 'success')
                if session.get('user_id'):
                    return redirect(url_for('user_bp.profile'))
                return redirect(url_for('auth_bp.login'))
        
        flash(message, 'danger')
    
    return render_template('auth/verify_email.html', email=email)


@auth.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Gửi lại mã OTP."""
    email = request.form.get('email')
    
    if not email:
        flash('Email không hợp lệ.', 'danger')
        return redirect(url_for('auth_bp.register'))
    
    otp_code, success, message = create_email_verification(email)
    if success:
        send_success, send_message = send_verification_email(email, otp_code)
        if send_success:
            flash('Mã OTP mới đã được gửi đến email của bạn.', 'success')
        else:
            flash(f'Không thể gửi email: {send_message}', 'danger')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('auth_bp.verify_email', email=email))


@auth.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    """Xử lý quên mật khẩu - gửi mã reset qua email."""
    # Check if user is already logged in
    user_id = session.get('user_id')
    current_user = None
    if user_id:
        current_user = User.query.get(user_id)

    if request.method == 'POST':
        # If logged in, force identifier to be current user's
        if current_user:
            identifier = current_user.email or current_user.student_staff_id
        else:
            identifier = request.form.get('identifier', '').strip()  # Email hoặc MSSV/MSCB
        
        if not identifier:
            flash('Vui lòng nhập email hoặc MSSV/MSCB.', 'danger')
            return render_template('auth/forgot_password.html', 
                                 is_logged_in=bool(current_user),
                                 current_user=current_user)
        
        # Tìm user theo email hoặc student_staff_id
        user = User.query.filter(
            (User.email == identifier) | (User.student_staff_id == identifier)
        ).first()
        
        if not user:
            flash('Không tìm thấy tài khoản với thông tin này.', 'danger')
            return render_template('auth/forgot_password.html', 
                                 is_logged_in=bool(current_user),
                                 current_user=current_user)
        
        # Security check: if logged in, ensure we're resetting the own account
        if current_user and user.id != current_user.id:
             flash('Bạn chỉ có thể reset mật khẩu cho tài khoản hiện tại.', 'danger')
             return render_template('auth/forgot_password.html', 
                                 is_logged_in=bool(current_user),
                                 current_user=current_user)

        if not user.email:
            flash('Tài khoản này chưa có email. Vui lòng liên hệ thủ thư.', 'danger')
            return render_template('auth/forgot_password.html', 
                                 admin_email=LIBRARY_ADMIN_EMAIL, 
                                 admin_phone=LIBRARY_ADMIN_PHONE,
                                 is_logged_in=bool(current_user),
                                 current_user=current_user)
        
        # Tạo và gửi reset code
        reset_code, success, message = create_password_reset(user.id)
        if success:
            send_success, send_message = send_password_reset_email(user.email, reset_code, user.username)
            if send_success:
                masked_email = mask_email(user.email)
                flash(f'Mã xác nhận đã được gửi đến email {masked_email} của tài khoản.', 'success')
                return redirect(url_for('auth_bp.reset_password', user_id=user.id))
            else:
                flash(f'Không thể gửi email: {send_message}', 'danger')
        else:
            flash(message, 'danger')
    
    return render_template('auth/forgot_password.html', 
                         admin_email=LIBRARY_ADMIN_EMAIL, 
                         admin_phone=LIBRARY_ADMIN_PHONE,
                         is_logged_in=bool(current_user),
                         current_user=current_user)


@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Trang đặt lại mật khẩu với mã xác nhận."""
    user_id = request.args.get('user_id', type=int) or request.form.get('user_id', type=int)
    
    if not user_id:
        flash('Yêu cầu không hợp lệ.', 'danger')
        return redirect(url_for('auth_bp.forgot_password'))
    
    user = User.query.get(user_id)
    if not user:
        flash('Người dùng không tồn tại.', 'danger')
        return redirect(url_for('auth_bp.forgot_password'))
    
    if request.method == 'POST':
        reset_code = request.form.get('reset_code', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not reset_code or not new_password or not confirm_password:
            flash('Vui lòng điền đầy đủ thông tin.', 'danger')
            return render_template('auth/reset_password.html', user_id=user_id)
        
        if new_password != confirm_password:
            flash('Mật khẩu xác nhận không khớp.', 'danger')
            return render_template('auth/reset_password.html', user_id=user_id)
        
        # Validate password strength
        def is_valid_password(pw: str) -> bool:
            if not pw or len(pw) < 6:
                return False
            return bool(re.search(r"(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9])", pw))
        
        if not is_valid_password(new_password):
            flash('Mật khẩu không hợp lệ. Yêu cầu: ít nhất 6 ký tự, bao gồm chữ, số và ký tự đặc biệt.', 'danger')
            return render_template('auth/reset_password.html', user_id=user_id)
        
        # Verify reset code
        success, message, reset_record = verify_reset_code(user_id, reset_code)
        if success:
            # Update password
            user.password_hash = hash_password(new_password)
            mark_reset_code_used(reset_record)
            db.session.commit()
            
            flash('Mật khẩu đã được đặt lại thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('auth_bp.login'))
        else:
            flash(message, 'danger')
    
    return render_template('auth/reset_password.html', user_id=user_id)