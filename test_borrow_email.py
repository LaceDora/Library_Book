from app import app, db
from models import User, Book, Borrow
from datetime import datetime, timedelta
from email_service import send_borrow_confirmation_email
from config import LOAN_PERIOD_DAYS

def test_borrow_email():
    with app.app_context():
        print("--- BẮT ĐẦU TEST EMAIL BORROW ---")
        
        # 1. Cấu hình email nhận test
        test_email = "huyphanquoc8@gmail.com"
        print(f"Email nhận test: {test_email}")
        
        # 2. Tìm user
        user = User.query.filter_by(email=test_email).first()
        if not user:
            print(f"Không tìm thấy user với email {test_email}")
            return

        # 3. Lấy sách
        book = Book.query.first()
        if not book:
            print("Không có sách nào.")
            return

        # 4. Giả lập thông số
        borrow_date = datetime.now()
        deadline = borrow_date + timedelta(days=LOAN_PERIOD_DAYS)
        
        print(f"Sách: {book.title}")
        print(f"Ngày mượn: {borrow_date}")
        print(f"Hạn trả: {deadline}")

        # 5. Gửi email trực tiếp (test hàm send_borrow_confirmation_email)
        print(">>> Đang gửi email...")
        success, msg = send_borrow_confirmation_email(test_email, user.username, book.title, book.author, borrow_date, deadline)
        
        if success:
            print(f"SUCCESS: {msg}")
        else:
            print(f"FAILED: {msg}")

        print("--- KẾT THÚC TEST ---")

if __name__ == "__main__":
    test_borrow_email()
