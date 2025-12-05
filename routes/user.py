
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
# Import custom password functions from auth.py
from routes.auth import hash_password, verify_password
from phone_service import create_phone_verification, verify_phone_otp, send_sms_otp
from email_service import create_email_verification, send_verification_email
from flask import jsonify

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

            # Validate password strength with detailed messages
            import re
            if not new_password or len(new_password) < 6:
                flash('Mật khẩu mới phải có ít nhất 6 ký tự.', 'danger')
                return redirect(url_for('user_bp.profile'))
            
            missing = []
            if not re.search(r'[A-Za-z]', new_password):
                missing.append('chữ cái')
            if not re.search(r'\d', new_password):
                missing.append('chữ số')
            if not re.search(r'[@$!%*#?&]', new_password):
                missing.append('ký tự đặc biệt (@$!%*#?&)')
            
            if missing:
                flash(f"Mật khẩu mới thiếu: {', '.join(missing)}", 'danger')
                return redirect(url_for('user_bp.profile'))

            if not current_password:
                flash('Vui lòng nhập mật khẩu hiện tại để đổi mật khẩu.', 'danger')
                return redirect(url_for('user_bp.profile'))

            if not verify_password(user.password_hash, current_password):
                flash('Mật khẩu hiện tại không đúng.', 'danger')
                return redirect(url_for('user_bp.profile'))

        try:
            # Cập nhật thông tin cơ bản
            user.username = new_username
            
            # Xử lý thay đổi email
            email_changed = False
            if new_email and new_email != user.email:
                user.email = new_email
                user.email_verified = False
                email_changed = True
            
            # Nếu đổi số điện thoại, reset trạng thái đã xác thực
            if user.phone != new_phone:
                user.phone = new_phone
                user.phone_verified = False

            # Cập nhật mật khẩu mới nếu có
            if new_password:
                user.password_hash = hash_password(new_password)

            # Lưu vào database
            db.session.commit()
            
            # Cập nhật session
            session['username'] = user.username
            
            # Nếu đổi email, gửi OTP và chuyển hướng đến trang xác thực
            if email_changed:
                otp_code, success, message = create_email_verification(user.email)
                if success:
                    send_success, send_message = send_verification_email(user.email, otp_code)
                    if send_success:
                        flash('Cập nhật email thành công! Vui lòng kiểm tra email mới để xác thực.', 'success')
                        return redirect(url_for('auth_bp.verify_email', email=user.email))
                    else:
                        flash(f'Cập nhật email nhưng không thể gửi mã xác thực: {send_message}', 'warning')
                else:
                    flash(f'Cập nhật email nhưng lỗi tạo mã xác thực: {message}', 'warning')
            
            flash('Cập nhật thông tin thành công!', 'success')
            return redirect(url_for('user_bp.profile'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating user profile: {str(e)}")  # Log lỗi để debug
            flash('Có lỗi xảy ra khi cập nhật thông tin. Vui lòng thử lại.', 'danger')
            return redirect(url_for('user_bp.profile'))

    return render_template('user/profile.html', user=user)

@user.route('/verify-phone/send', methods=['POST'])
def send_phone_otp():
    """API gửi mã OTP xác thực số điện thoại."""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
        
    user = User.query.get(session['user_id'])
    if not user or not user.phone:
        return jsonify({'success': False, 'message': 'Vui lòng cập nhật số điện thoại trước.'}), 400
        
    if user.phone_verified:
        return jsonify({'success': False, 'message': 'Số điện thoại đã được xác thực.'}), 400
        
    otp_code, success, message = create_phone_verification(user.phone)
    if success:
        send_success, send_message = send_sms_otp(user.phone, otp_code)
        if send_success:
            return jsonify({'success': True, 'message': send_message})
        else:
            return jsonify({'success': False, 'message': send_message}), 500
    else:
        return jsonify({'success': False, 'message': message}), 400

@user.route('/verify-phone/confirm', methods=['POST'])
def confirm_phone_otp():
    """API xác nhận mã OTP."""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
        
    user = User.query.get(session['user_id'])
    if not user or not user.phone:
        return jsonify({'success': False, 'message': 'Vui lòng cập nhật số điện thoại trước.'}), 400
        
    data = request.get_json()
    otp_code = data.get('otp_code')
    
    if not otp_code:
        return jsonify({'success': False, 'message': 'Vui lòng nhập mã OTP.'}), 400
        
    success, message = verify_phone_otp(user.phone, otp_code)
    if success:
        user.phone_verified = True
        db.session.commit()
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@user.route('/borrows')
def borrows():
    if not session.get("user_id"):
        flash("Vui lòng đăng nhập để xem lịch sử mượn!", "warning")
        return redirect(url_for("auth_bp.login"))
    user_id = session["user_id"]
    records = Borrow.query.filter_by(user_id=user_id).order_by(Borrow.borrow_date.desc()).all()
    return render_template("user/borrows.html", records=records)

# @user.route('/users')
# def users_list():
#     all_users = User.query.all()
#     return render_template('users.html', users=all_users)
# 
# @user.route('/users/<int:user_id>')
# def user_detail(user_id):
#     user = User.query.get_or_404(user_id)
#     records = Borrow.query.filter_by(user_id=user_id).all()
#     return render_template('user_history.html', user=user, records=records)

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