"""decorators.py

Chứa decorator dùng chung cho routes (hiện có: admin_required).

admin_required: kiểm tra user đã đăng nhập và có quyền admin.
 - Nếu chưa đăng nhập: chuyển hướng đến trang đăng nhập (flash thông báo).
 - Nếu không phải admin: chuyển hướng về trang chủ với thông báo lỗi.

Gợi ý: nếu dùng nhiều decorator, có thể tách thành login_required chung và admin_required chỉ bổ sung quyền admin.
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def admin_required(f):
    """Decorator bảo vệ route chỉ cho admin truy cập.

    Hành vi:
    - nếu không có session['user_id'] -> flash + redirect tới trang login
    - nếu có nhưng session['is_admin'] != True -> flash + redirect về trang chính
    - nếu OK -> tiếp tục gọi view function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Vui lòng đăng nhập để truy cập.', 'warning')
            return redirect(url_for('auth_bp.login'))
        if not session.get('is_admin'):
            flash('Chỉ admin mới có thể truy cập trang này.', 'danger')
            return redirect(url_for('main_bp.index'))
        return f(*args, **kwargs)
    return decorated_function