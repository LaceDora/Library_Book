from app import app, db, check_overdue_books
from models import User, Book, Borrow
from datetime import datetime, timedelta

def test_reminder():
    with app.app_context():
        print("--- BẮT ĐẦU TEST EMAIL REMINDER ---")
        
        # 1. Cấu hình email nhận test
        # HÃY SỬA EMAIL DƯỚI ĐÂY THÀNH EMAIL CỦA BẠN
        test_email = "huyphanquoc8@gmail.com"  # <--- SỬA TẠI ĐÂY
        
        print(f"Email nhận test: {test_email}")
        
        # 2. Tìm hoặc tạo User test
        user = User.query.filter_by(email=test_email).first()
        if not user:
            print(f"Không tìm thấy user với email {test_email}. Đang tạo user tạm...")
            # Tạo user tạm với ID ngẫu nhiên để tránh trùng
            import uuid
            user = User(
                username="Test User", 
                email=test_email, 
                student_staff_id=f"TEST_{uuid.uuid4().hex[:6]}", 
                password_hash="dummy",
                role="student"
            )
            db.session.add(user)
            db.session.commit()
            print(f"Đã tạo user test ID: {user.id}")
        else:
            print(f"Sử dụng user hiện có ID: {user.id}")

        # 3. Lấy một cuốn sách bất kỳ
        book = Book.query.first()
        if not book:
            print("Lỗi: Không có sách nào trong DB để test.")
            return

        # 4. Tạo record mượn sách giả lập có hạn trả là NGÀY MAI
        # Vì logic trong app.py tìm sách có hạn trả vào ngày mai
        tomorrow = datetime.now() + timedelta(days=1)
        # Set giờ là 12:00 trưa mai
        tomorrow = tomorrow.replace(hour=12, minute=0, second=0)
        
        borrow = Borrow(
            user_id=user.id,
            book_id=book.id,
            borrow_date=datetime.now(),
            return_date=tomorrow,
            book_title=book.title
        )
        db.session.add(borrow)
        db.session.commit()
        print(f"Đã tạo phiếu mượn giả lập: Sách '{book.title}', Hạn trả: {tomorrow.strftime('%d/%m/%Y')}")

        # 5. Chạy hàm kiểm tra (giả lập việc Scheduler chạy)
        print("\n>>> Đang chạy check_overdue_books()...")
        try:
            check_overdue_books()
            print(">>> Hàm đã chạy xong.")
        except Exception as e:
            print(f"!!! Lỗi khi chạy hàm: {e}")

        # 6. Dọn dẹp dữ liệu test
        print("\n--- Dọn dẹp dữ liệu test ---")
        db.session.delete(borrow)
        # Nếu user là user test mới tạo thì xóa luôn, còn user cũ thì giữ
        if user.student_staff_id.startswith("TEST_"):
            db.session.delete(user)
            print("Đã xóa user test.")
        else:
            print("Giữ lại user (vì là user có sẵn).")
            
        db.session.commit()
        print("Đã xóa phiếu mượn test.")
        print("--- KẾT THÚC TEST ---")

if __name__ == "__main__":
    test_reminder()
