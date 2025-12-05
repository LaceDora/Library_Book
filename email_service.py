"""email_service.py

Service để xử lý gửi email và quản lý OTP/reset codes.

Chức năng:
- Tạo và lưu OTP code cho email verification
- Tạo và lưu reset code cho password reset
- Gửi email qua Flask-Mail
- Verify OTP/reset codes
- Rate limiting để tránh spam
"""

from flask_mail import Mail, Message
from models import db, EmailVerification, PasswordReset, User
from datetime import datetime, timedelta
import random
import string

mail = Mail()


def generate_otp_code(length=6):
    """Tạo mã OTP ngẫu nhiên gồm 6 chữ số."""
    return ''.join(random.choices(string.digits, k=length))


def create_email_verification(email):
    """Tạo OTP code mới cho email verification.
    
    Args:
        email: Email cần xác thực
        
    Returns:
        tuple: (otp_code, success, message)
    """
    # Kiểm tra rate limiting: tối đa 3 lần trong 10 phút
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    recent_attempts = EmailVerification.query.filter(
        EmailVerification.email == email,
        EmailVerification.created_at >= ten_minutes_ago
    ).count()
    
    if recent_attempts >= 3:
        return None, False, "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau 10 phút."
    
    # Xóa các OTP cũ chưa verify của email này
    EmailVerification.query.filter_by(email=email, verified=False).delete()
    
    # Tạo OTP mới
    otp_code = generate_otp_code()
    expires_at = datetime.now() + timedelta(minutes=10)
    
    verification = EmailVerification(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    db.session.add(verification)
    db.session.commit()
    
    return otp_code, True, "OTP đã được tạo thành công."


def verify_otp_code(email, otp_code):
    """Xác thực OTP code.
    
    Args:
        email: Email cần xác thực
        otp_code: Mã OTP người dùng nhập
        
    Returns:
        tuple: (success, message)
    """
    verification = EmailVerification.query.filter_by(
        email=email,
        otp_code=otp_code,
        verified=False
    ).first()
    
    if not verification:
        return False, "Mã OTP không hợp lệ."
    
    if datetime.now() > verification.expires_at:
        return False, "Mã OTP đã hết hạn. Vui lòng yêu cầu mã mới."
    
    # Đánh dấu đã verify
    verification.verified = True
    db.session.commit()
    
    return True, "Xác thực email thành công!"


def create_password_reset(user_id):
    """Tạo reset code mới cho password reset.
    
    Args:
        user_id: ID của user yêu cầu reset
        
    Returns:
        tuple: (reset_code, success, message)
    """
    # Kiểm tra rate limiting: tối đa 3 lần trong 10 phút
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    recent_attempts = PasswordReset.query.filter(
        PasswordReset.user_id == user_id,
        PasswordReset.created_at >= ten_minutes_ago
    ).count()
    
    if recent_attempts >= 3:
        return None, False, "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau 10 phút."
    
    # Xóa các reset code cũ chưa dùng
    PasswordReset.query.filter_by(user_id=user_id, used=False).delete()
    
    # Tạo reset code mới
    reset_code = generate_otp_code()
    expires_at = datetime.now() + timedelta(minutes=15)
    
    reset = PasswordReset(
        user_id=user_id,
        reset_code=reset_code,
        expires_at=expires_at
    )
    
    db.session.add(reset)
    db.session.commit()
    
    return reset_code, True, "Mã reset đã được tạo thành công."


def verify_reset_code(user_id, reset_code):
    """Xác thực reset code.
    
    Args:
        user_id: ID của user
        reset_code: Mã reset người dùng nhập
        
    Returns:
        tuple: (success, message, reset_record)
    """
    reset = PasswordReset.query.filter_by(
        user_id=user_id,
        reset_code=reset_code,
        used=False
    ).first()
    
    if not reset:
        return False, "Mã xác nhận không hợp lệ.", None
    
    if datetime.now() > reset.expires_at:
        return False, "Mã xác nhận đã hết hạn. Vui lòng yêu cầu mã mới.", None
    
    return True, "Mã xác nhận hợp lệ.", reset


def mark_reset_code_used(reset_record):
    """Đánh dấu reset code đã được sử dụng."""
    reset_record.used = True
    db.session.commit()


def send_verification_email(email, otp_code):
    """Gửi email chứa OTP code.
    
    Args:
        email: Email người nhận
        otp_code: Mã OTP
        
    Returns:
        tuple: (success, message)
    """
    try:
        msg = Message(
            subject="Xác thực tài khoản - Hệ thống Thư viện",
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Xác thực tài khoản</h2>
                <p>Xin chào,</p>
                <p>Cảm ơn bạn đã đăng ký tài khoản tại Hệ thống Thư viện.</p>
                <p>Mã OTP của bạn là:</p>
                <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #007bff; margin: 0; letter-spacing: 5px;">{otp_code}</h1>
                </div>
                <p>Mã này có hiệu lực trong <strong>10 phút</strong>.</p>
                <p>Nếu bạn không yêu cầu xác thực này, vui lòng bỏ qua email này.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">Email này được gửi tự động, vui lòng không trả lời.</p>
            </div>
            """
        )
        mail.send(msg)
        return True, "Email đã được gửi thành công."
    except Exception as e:
        return False, f"Lỗi khi gửi email: {str(e)}"


def send_password_reset_email(email, reset_code, username):
    """Gửi email chứa reset code.
    
    Args:
        email: Email người nhận
        reset_code: Mã reset
        username: Tên người dùng
        
    Returns:
        tuple: (success, message)
    """
    try:
        msg = Message(
            subject="Đặt lại mật khẩu - Hệ thống Thư viện",
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Đặt lại mật khẩu</h2>
                <p>Xin chào <strong>{username}</strong>,</p>
                <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.</p>
                <p>Mã xác nhận của bạn là:</p>
                <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #dc3545; margin: 0; letter-spacing: 5px;">{reset_code}</h1>
                </div>
                <p>Mã này có hiệu lực trong <strong>15 phút</strong>.</p>
                <p>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này và đảm bảo tài khoản của bạn an toàn.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">Email này được gửi tự động, vui lòng không trả lời.</p>
            </div>
            """
        )
        mail.send(msg)
        return True, "Email đã được gửi thành công."
    except Exception as e:
        return False, f"Lỗi khi gửi email: {str(e)}"

def send_return_reminder_email(email, username, book_title, return_date):
    """Gửi email nhắc nhở trả sách.
    
    Args:
        email: Email người nhận
        username: Tên người dùng
        book_title: Tên sách
        return_date: Ngày phải trả (datetime object)
        
    Returns:
        tuple: (success, message)
    """
    try:
        formatted_date = return_date.strftime('%d/%m/%Y')
        msg = Message(
            subject="Nhắc nhở trả sách - Hệ thống Thư viện",
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Nhắc nhở trả sách</h2>
                <p>Xin chào <strong>{username}</strong>,</p>
                <p>Đây là email nhắc nhở về việc trả sách tại thư viện.</p>
                <p>Bạn có cuốn sách <strong>"{book_title}"</strong> cần phải trả vào ngày:</p>
                <div style="background-color: #fff3cd; padding: 20px; text-align: center; margin: 20px 0; border: 1px solid #ffeeba;">
                    <h2 style="color: #856404; margin: 0;">{formatted_date}</h2>
                </div>
                <p>Vui lòng sắp xếp thời gian đến thư viện để trả sách đúng hạn.</p>
                <p>Nếu bạn đã trả sách, vui lòng bỏ qua email này.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">Email này được gửi tự động, vui lòng không trả lời.</p>
            </div>
            """
        )
        mail.send(msg)
        return True, "Email nhắc nhở đã được gửi thành công."
    except Exception as e:
        return False, f"Lỗi khi gửi email: {str(e)}"

def send_borrow_confirmation_email(email, username, book_title, book_author, borrow_date, return_deadline):
    """Gửi email xác nhận đăng ký mượn sách (chờ duyệt).
    
    Args:
        email: Email người nhận
        username: Tên người dùng
        book_title: Tên sách
        book_author: Tác giả
        borrow_date: Ngày mượn dự kiến (datetime object)
        return_deadline: Ngày trả dự kiến (datetime object)
        
    Returns:
        tuple: (success, message)
    """
    try:
        formatted_borrow_date = borrow_date.strftime('%d/%m/%Y')
        formatted_deadline = return_deadline.strftime('%d/%m/%Y')
        
        msg = Message(
            subject="Đăng ký mượn sách thành công - Hệ thống Thư viện",
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #ffc107;">Đăng ký mượn sách thành công!</h2>
                <p>Xin chào <strong>{username}</strong>,</p>
                <p>Bạn đã đăng ký mượn thành công cuốn sách:</p>
                <h3 style="color: #333;">{book_title}</h3>
                <p style="color: #666; font-style: italic;">Tác giả: {book_author}</p>
                
                <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <p><strong>Ngày mượn dự kiến:</strong> {formatted_borrow_date}</p>
                    <p><strong>Ngày trả dự kiến:</strong> <span style="color: #dc3545; font-weight: bold;">{formatted_deadline}</span></p>
                </div>
                
                <div style="background-color: #d1ecf1; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                    <p style="margin: 0;"><strong>⏳ Trạng thái:</strong> Chờ admin duyệt</p>
                </div>
                
                <p>Vui lòng đến thư viện sau khi admin duyệt yêu cầu của bạn để nhận sách.</p>
                <p>Bạn sẽ nhận được thông báo qua email khi yêu cầu được duyệt.</p>
                <p>Chúc bạn đọc sách vui vẻ!</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">Email này được gửi tự động, vui lòng không trả lời.</p>
            </div>
            """
        )
        mail.send(msg)
        return True, "Email xác nhận đã được gửi thành công."
    except Exception as e:
        return False, f"Lỗi khi gửi email: {str(e)}"

def send_borrow_approved_email(email, username, book_title, book_author, borrow_date, return_deadline):
    """Gửi email thông báo yêu cầu mượn sách đã được duyệt.
    
    Args:
        email: Email người nhận
        username: Tên người dùng
        book_title: Tên sách
        book_author: Tác giả
        borrow_date: Ngày mượn (datetime object)
        return_deadline: Hạn trả (datetime object)
        
    Returns:
        tuple: (success, message)
    """
    try:
        formatted_borrow_date = borrow_date.strftime('%d/%m/%Y')
        formatted_deadline = return_deadline.strftime('%d/%m/%Y')
        
        msg = Message(
            subject="Yêu cầu mượn sách đã được duyệt - Hệ thống Thư viện",
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #28a745;">✅ Yêu cầu mượn sách đã được duyệt!</h2>
                <p>Xin chào <strong>{username}</strong>,</p>
                <p>Yêu cầu mượn sách của bạn đã được admin duyệt:</p>
                <h3 style="color: #333;">{book_title}</h3>
                <p style="color: #666; font-style: italic;">Tác giả: {book_author}</p>
                
                <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                    <p><strong>Ngày mượn:</strong> {formatted_borrow_date}</p>
                    <p><strong>Hạn trả:</strong> <span style="color: #dc3545; font-weight: bold;">{formatted_deadline}</span></p>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <p style="margin: 0;"><strong>📍 Vui lòng đến thư viện để nhận sách!</strong></p>
                </div>
                
                <p>Vui lòng trả sách đúng hạn để tránh bị phạt.</p>
                <p>Chúc bạn đọc sách vui vẻ!</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">Email này được gửi tự động, vui lòng không trả lời.</p>
            </div>
            """
        )
        mail.send(msg)
        return True, "Email thông báo duyệt đã được gửi thành công."
    except Exception as e:
        return False, f"Lỗi khi gửi email: {str(e)}"

def send_borrow_rejected_email(email, username, book_title, book_author):
    """Gửi email thông báo yêu cầu mượn sách bị từ chối.
    
    Args:
        email: Email người nhận
        username: Tên người dùng
        book_title: Tên sách
        book_author: Tác giả
        
    Returns:
        tuple: (success, message)
    """
    try:
        msg = Message(
            subject="Yêu cầu mượn sách bị từ chối - Hệ thống Thư viện",
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc3545;">❌ Yêu cầu mượn sách bị từ chối</h2>
                <p>Xin chào <strong>{username}</strong>,</p>
                <p>Rất tiếc, yêu cầu mượn sách của bạn đã bị từ chối:</p>
                <h3 style="color: #333;">{book_title}</h3>
                <p style="color: #666; font-style: italic;">Tác giả: {book_author}</p>
                
                <div style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Lý do có thể:</strong></p>
                    <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                        <li>Sách đã hết</li>
                        <li>Sách đang được bảo trì</li>
                        <li>Yêu cầu không hợp lệ</li>
                    </ul>
                </div>
                
                <p>Vui lòng liên hệ thủ thư để biết thêm chi tiết hoặc đăng ký mượn sách khác.</p>
                <p><strong>Email:</strong> quochuyphan2k5@gmail.com</p>
                <p><strong>SĐT:</strong> 0917715034</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">Email này được gửi tự động, vui lòng không trả lời.</p>
            </div>
            """
        )
        mail.send(msg)
        return True, "Email thông báo từ chối đã được gửi thành công."
    except Exception as e:
        return False, f"Lỗi khi gửi email: {str(e)}"

