"""routes/auth.py

Routes liên quan tới xác thực người dùng:
 - login: đăng nhập bằng `student_staff_id` (MSSV/MSCB) và password
 - logout: xóa session
 - register: tạo tài khoản mới (kiểm tra trùng MSSV/MSCB)

Ghi chú: `username` ở model là tên hiển thị, không dùng để đăng nhập (đăng nhập bằng student_staff_id).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import hashlib
import os
from config import LIBRARY_ADMIN_EMAIL, LIBRARY_ADMIN_PHONE
import re

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

@auth.route("/login", methods=["GET", "POST"])
def login():
    """Xử lý POST/GET cho trang login.

    POST:
    - Lấy `login` field (MSSV/MSCB) và `password`.
    - Tìm user theo `student_staff_id` và so sánh hash.
    - Nếu ok, lưu session và redirect.
    """
    if request.method == "POST":
        student_staff_id = request.form["login"]  # Form vẫn dùng name="login" nhưng chỉ nhận MSSV/MSCB
        password = request.form["password"]

        # Chỉ tìm user theo student_staff_id
        user = User.query.filter_by(student_staff_id=student_staff_id).first()

        if not user:
            flash("Sai MSSV/MSCB hoặc mật khẩu!", "danger")
        elif not user.is_active:
            flash("Tài khoản này đã bị khoá. Liên hệ thủ thư để được hỗ trợ.", "danger")
        elif verify_password(user.password_hash, password):
            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            session["username"] = user.username
            session["role"] = user.role
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for("main_bp.index"))
    return render_template("login.html")

@auth.route("/logout")
def logout():
    """Xóa session và redirect về trang chủ."""
    session.clear()
    flash("Đã đăng xuất!", "info")
    return redirect(url_for("main_bp.index"))

@auth.route("/register", methods=["GET", "POST"])
def register():
    """Xử lý đăng ký tài khoản.

    POST:
    - Kiểm tra password/confirm
    - Kiểm tra trùng `student_staff_id`
    - Tạo User với password hash
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_confirm = request.form["password_confirm"]
        student_staff_id = request.form["student_staff_id"]

        if password != password_confirm:
            flash("Mật khẩu xác nhận không khớp!", "danger")
            return render_template("register.html")

        # Kiểm tra độ mạnh mật khẩu: ít nhất 6 ký tự, có chữ, số và ký tự đặc biệt
        def is_valid_password(pw: str) -> bool:
            if not pw or len(pw) < 6:
                return False
            # regex: at least one letter, one digit, one non-alphanumeric
            return bool(re.search(r"(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9])", pw))

        if not is_valid_password(password):
            flash("Mật khẩu không hợp lệ. Yêu cầu: ít nhất 6 ký tự, bao gồm chữ, số và ký tự đặc biệt.", "danger")
            return render_template("register.html")

        # Chỉ kiểm tra trùng MSSV/MSCB
        if User.query.filter_by(student_staff_id=student_staff_id).first():
            flash("MSSV/MSCB này đã được đăng ký!", "danger")
        else:
            role = request.form.get("role", "student")
            if role not in ["student", "staff"]:
                role = "student"

            user = User(
                username=username,
                password_hash=hash_password(password),
                student_staff_id=student_staff_id,
                role=role
            )
            db.session.add(user)
            db.session.commit()
            flash("Đăng ký thành công! Hãy đăng nhập.", "success")
            return redirect(url_for("auth_bp.login"))
    return render_template("register.html")


@auth.route('/forgot', methods=['GET'])
def forgot_password():
    """Hiển thị trang liên hệ thủ thư khi user quên mật khẩu."""
    # Lấy thông tin liên hệ từ config
    return render_template('forgot_password.html', admin_email=LIBRARY_ADMIN_EMAIL, admin_phone=LIBRARY_ADMIN_PHONE)