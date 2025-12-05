"""phone_service.py

Service để xử lý xác thực số điện thoại.

Chức năng:
- Tạo và lưu OTP code cho phone verification
- Mock gửi SMS (in ra console)
- Verify OTP codes
- Rate limiting
"""

from models import db, PhoneVerification
from datetime import datetime, timedelta
import random
import string

def generate_otp_code(length=6):
    """Tạo mã OTP ngẫu nhiên gồm 6 chữ số."""
    return ''.join(random.choices(string.digits, k=length))

def create_phone_verification(phone):
    """Tạo OTP code mới cho phone verification.
    
    Args:
        phone: Số điện thoại cần xác thực
        
    Returns:
        tuple: (otp_code, success, message)
    """
    # Kiểm tra rate limiting: tối đa 3 lần trong 5 phút
    five_minutes_ago = datetime.now() - timedelta(minutes=5)
    recent_attempts = PhoneVerification.query.filter(
        PhoneVerification.phone == phone,
        PhoneVerification.created_at >= five_minutes_ago
    ).count()
    
    if recent_attempts >= 3:
        return None, False, "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau 5 phút."
    
    # Xóa các OTP cũ chưa verify của sđt này
    PhoneVerification.query.filter_by(phone=phone, verified=False).delete()
    
    # Tạo OTP mới
    otp_code = generate_otp_code()
    expires_at = datetime.now() + timedelta(minutes=5)
    
    verification = PhoneVerification(
        phone=phone,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    db.session.add(verification)
    db.session.commit()
    
    return otp_code, True, "OTP đã được tạo thành công."

def verify_phone_otp(phone, otp_code):
    """Xác thực OTP code.
    
    Args:
        phone: Số điện thoại
        otp_code: Mã OTP người dùng nhập
        
    Returns:
        tuple: (success, message)
    """
    verification = PhoneVerification.query.filter_by(
        phone=phone,
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
    
    return True, "Xác thực số điện thoại thành công!"

def send_sms_otp(phone, otp_code):
    """Giả lập gửi SMS chứa OTP code.
    
    Trong thực tế sẽ gọi API của bên thứ 3 (Twilio, Vonage...).
    Ở đây chỉ in ra console.
    
    Args:
        phone: Số điện thoại người nhận
        otp_code: Mã OTP
        
    Returns:
        tuple: (success, message)
    """
    try:
        # MOCK SENDING
        print(f"\n{'='*40}")
        print(f" [MOCK SMS] Sending to {phone}")
        print(f" Message: Mã xác thực của bạn là {otp_code}")
        print(f"{'='*40}\n")
        
        return True, "Mã xác thực đã được gửi (kiểm tra console)."
    except Exception as e:
        return False, f"Lỗi khi gửi SMS: {str(e)}"
