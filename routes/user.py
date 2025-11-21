
"""routes/user.py

Chứa các route liên quan tới user:
 - profile: xem và cập nhật thông tin cá nhân, upload avatar, đổi mật khẩu
 - borrows: danh sách lịch sử mượn của user
 - list_users, history, delete_user: các chức năng quản lý user (chỉ admin)

Ghi chú:
 - Xử lý upload có kiểm tra size (2MB) và extension thông qua helper `allowed_file`.
 - Khi xóa user, các borrow chưa trả sẽ được xử lý và số lượng sách được phục hồi tương ứng.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.exceptions import RequestEntityTooLarge
from models import db, User, Book, Borrow, Audit
from decorators import admin_required
from datetime import datetime
from config import allowed_file, UPLOAD_FOLDER
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

user = Blueprint('user', __name__)

@user.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('user_id'):
        flash('Phiên đăng nhập đã hết hạn hoặc bạn chưa đăng nhập. Vui lòng đăng nhập lại!', 'warning')
        return redirect(url_for('auth_bp.login'))

    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip() or None
        new_phone = request.form.get('phone', '').strip() or None
        new_password = request.form.get('password')
        current_password = request.form.get('current_password')

        # Check for duplicates
        if new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Tên đăng nhập đã tồn tại, vui lòng chọn tên khác.', 'danger')
                return redirect(url_for('user_bp.profile'))

        if new_email and new_email != user.email:
            if User.query.filter(User.email == new_email, User.id != user.id).first():
                flash('Email này đã được sử dụng bởi người dùng khác.', 'danger')
                return redirect(url_for('user_bp.profile'))

        if new_phone and new_phone != user.phone:
            if User.query.filter(User.phone == new_phone, User.id != user.id).first():
                flash('Số điện thoại này đã được sử dụng bởi người dùng khác.', 'danger')
                return redirect(url_for('user_bp.profile'))

        # Handle avatar upload
        try:
            file = request.files.get('avatar')
            if file and file.filename:
                # Kiểm tra định dạng file
                if not allowed_file(file.filename):
                    flash('Chỉ chấp nhận file ảnh: png, jpg, jpeg, gif', 'danger')
                    return redirect(url_for('user_bp.profile'))
                
                # Đọc và kiểm tra kích thước file
                try:
                    file_content = file.read()
                    file.seek(0)  # Reset con trỏ file để đọc lại sau
                    
                    # Kiểm tra kích thước
                    if len(file_content) > 2 * 1024 * 1024:  # 2MB
                        flash('File ảnh quá lớn. Giới hạn 2MB.', 'danger')
                        return redirect(url_for('user_bp.profile'))
                    
                    # Xử lý tên file và lưu
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = secure_filename(f"user_{user.id}_avatar_{int(datetime.now().timestamp())}.{ext}")
                    
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    dest = os.path.join(UPLOAD_FOLDER, filename)
                    
                    # Xóa avatar cũ nếu có
                    if user.avatar_url:
                        try:
                            old_file = os.path.join(UPLOAD_FOLDER, os.path.basename(user.avatar_url))
                            if os.path.exists(old_file):
                                os.remove(old_file)
                        except Exception as e:
                            print(f"Lỗi khi xóa avatar cũ: {str(e)}")
                    
                    # Lưu file mới
                    file.save(dest)
                    user.avatar_url = f"/static/uploads/{filename}"
                
                except Exception as e:
                    print(f"Lỗi khi xử lý file upload: {str(e)}")
                    flash('Có lỗi xảy ra khi tải ảnh lên. Vui lòng thử lại.', 'danger')
                    return redirect(url_for('user_bp.profile'))
                    
        except RequestEntityTooLarge:
            flash('File ảnh quá lớn. Giới hạn là 2MB.', 'danger')
            return redirect(url_for('user_bp.profile'))

        # Xử lý thay đổi mật khẩu trước
        if new_password:
            password_confirm = request.form.get('password_confirm')
            if new_password != password_confirm:
                flash('Mật khẩu mới và xác nhận mật khẩu không khớp.', 'danger')
                return redirect(url_for('user_bp.profile'))

            if not current_password:
                flash('Vui lòng nhập mật khẩu hiện tại để đổi mật khẩu.', 'danger')
                return redirect(url_for('user_bp.profile'))

            if not check_password_hash(user.password_hash, current_password):
                flash('Mật khẩu hiện tại không đúng.', 'danger')
                return redirect(url_for('user_bp.profile'))

        try:
            # Cập nhật thông tin cơ bản
            user.username = new_username
            user.email = new_email
            user.phone = new_phone

            # Cập nhật mật khẩu mới nếu có
            if new_password:
                user.password_hash = generate_password_hash(new_password)

            # Lưu vào database
            db.session.commit()
            
            # Cập nhật session
            session['username'] = user.username
            
            flash('Cập nhật thông tin thành công!', 'success')
            return redirect(url_for('user_bp.profile'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating user profile: {str(e)}")  # Log lỗi để debug
            flash('Có lỗi xảy ra khi cập nhật thông tin. Vui lòng thử lại.', 'danger')
            return redirect(url_for('user_bp.profile'))

    return render_template('profile.html', user=user)

@user.route('/borrows')
def borrows():
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để xem lịch sử mượn!", "warning")
        return redirect(url_for("auth_bp.login"))
    user_id = session["user_id"]
    records = Borrow.query.filter_by(user_id=user_id).order_by(Borrow.borrow_date.desc()).all()
    return render_template("borrows.html", records=records)

@user.route('/users')
@admin_required
def list_users():
    all_users = User.query.order_by(User.id.asc()).all()
    return render_template('users.html', users=all_users)

@user.route('/user_history/<int:user_id>')
@admin_required
def history(user_id):
    user = User.query.get_or_404(user_id)
    records = Borrow.query.filter_by(user_id=user_id).order_by(Borrow.borrow_date.desc()).all()
    return render_template('user_history.html', user=user, records=records)

@user.route('/delete_user/<int:user_id>')
@admin_required
def delete(user_id):
    if session.get('user_id') == user_id:
        flash('Bạn không thể xóa chính mình.', 'warning')
        return redirect(url_for('user.list_users'))
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Không thể xóa user admin.', 'danger')
        return redirect(url_for('user.list_users'))
        
    borrows = Borrow.query.filter_by(user_id=user_id).all()
    processed_ids = []
    restored_per_book = {}

    for b in borrows:
        processed_ids.append(b.id)
        if not b.return_date:
            book = Book.query.get(b.book_id)
            if book:
                book.available_quantity = (book.available_quantity or 0) + 1
                restored_per_book[b.book_id] = restored_per_book.get(b.book_id, 0) + 1
        db.session.delete(b)

    details = f'Admin {session.get("user_id")} deleted user {user_id}. '
    details += f'Processed borrows: {processed_ids}.'
    if restored_per_book:
        details += f' Restored counts: {restored_per_book}.'

    try:
        audit = Audit(
            action='delete_user',
            actor_user_id=session.get('user_id'),
            target_borrow_id=None,
            target_book_id=None,
            details=details
        )
        db.session.add(audit)
    except Exception:
        db.session.rollback()

    db.session.delete(user)
    db.session.commit()
    flash('Đã xóa user và lịch sử mượn liên quan.', 'info')
    return redirect(url_for('user_bp.list_users'))