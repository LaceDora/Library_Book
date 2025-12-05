# GHI CHÚ DỰ ÁN - Thư viện Python Web App

> **Tài liệu đầy đủ về hệ thống quản lý thư viện**  
> Cập nhật: 2025-12-05

---

## 📌 MỤC LỤC

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Luồng hoạt động chính](#2-luồng-hoạt-động-chính)
3. [Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
4. [Chi tiết các file chính](#4-chi-tiết-các-file-chính)
5. [Database Models](#5-database-models)
6. [Gợi ý cải tiến](#6-gợi-ý-cải-tiến)

---

## 1. TỔNG QUAN HỆ THỐNG

### Công nghệ sử dụng
- **Backend**: Flask (Python 3.10)
- **Database**: MySQL + SQLAlchemy ORM
- **Frontend**: Bootstrap 5.3, Vanilla JavaScript
- **AI**: Google Gemini API + ChromaDB (RAG)
- **Email**: SMTP (Gmail)

### Tính năng chính
✅ **User Features:**
- Đăng ký/Đăng nhập (MSSV/MSCB hoặc Email + Password)
- Xác thực email (OTP)
- Tìm kiếm & lọc sách theo danh mục
- Đăng ký mượn sách (pending approval)
- Xem lịch sử mượn & trạng thái
- Chatbot AI hỗ trợ tìm sách
- Nhận thông báo real-time

✅ **Admin Features:**
- Dashboard thống kê
- Quản lý sách (CRUD)
- Quản lý người dùng
- Duyệt/Từ chối yêu cầu mượn sách
- Xem lịch sử mượn theo user
- Audit logs
- Nhận thông báo về yêu cầu mới

---

## 2. LUỒNG HOẠT ĐỘNG CHÍNH

### 🔹 A. Quy trình User mượn sách

```
1. USER: Đăng ký tài khoản
   ├─ Điền form (MSSV/MSCB, Email, Password)
   ├─ Hệ thống gửi OTP qua email
   └─ Xác thực email → Tài khoản active

2. USER: Đăng nhập
   ├─ Nhập MSSV/MSCB hoặc Email + Password
   └─ Session được tạo

3. USER: Tìm & xem sách
   ├─ Trang chủ: Popular + Latest books
   ├─ Tìm kiếm theo tên/tác giả
   ├─ Lọc theo danh mục
   └─ Xem chi tiết sách

4. USER: Đăng ký mượn sách
   ├─ Click "Đăng ký mượn"
   ├─ Chọn ngày mượn + ngày trả dự kiến (modal)
   ├─ Submit form
   ├─ Status: PENDING (chờ admin duyệt)
   ├─ Hệ thống GỬI THÔNG BÁO cho ALL ADMINS
   └─ Email xác nhận "Yêu cầu đã được gửi"

5. ADMIN: Nhận thông báo
   ├─ Notification bell hiện số lượng yêu cầu mới
   ├─ Click notification → redirect tới Manage Borrows (pending)
   └─ Xem chi tiết yêu cầu

6. ADMIN: Duyệt yêu cầu
   ├─ Click "Approve"
   │  ├─ Giảm quantity sách
   │  ├─ Status → APPROVED
   │  ├─ GỬI EMAIL xác nhận cho user
   │  └─ GỬI THÔNG BÁO cho user
   ├─ Hoặc click "Reject"
   │  ├─ Status → REJECTED
   │  ├─ GỬI EMAIL từ chối cho user
   │  └─ GỬI THÔNG BÁO cho user
   └─ Tạo Audit Log

7. USER: Nhận kết quả
   ├─ Nhận notification bell
   ├─ Click notification → xem lịch sử mượn
   ├─ Nhận email
   └─ Xem status: APPROVED/REJECTED trong "Lịch sử mượn"

8. USER: Trả sách (offline tại thư viện)
   ├─ Admin xác nhận trả sách
   ├─ Nhập tình trạng sách (good/damaged/lost)
   ├─ Tăng quantity (nếu good)
   └─ Cập nhật return_date
```

---

### 🔹 B. Hệ thống Notification

```
┌─────────────────────────────────────────────────┐
│         NOTIFICATION TRIGGERS                    │
├─────────────────────────────────────────────────┤
│ 1. User mượn sách → Notify ALL admins          │
│ 2. Admin approve  → Notify user                 │
│ 3. Admin reject   → Notify user                 │
└─────────────────────────────────────────────────┘

Cách hoạt động:
- Backend tạo bản ghi trong table `notification`
- Frontend poll API /notification/notifications mỗi 30s
- Hiển thị badge với số lượng unread
- Click notification → redirect đến link liên quan
- Mark as read khi click
```

---

### 🔹 C. Chatbot AI Flow

```
1. User click chatbot button (bottom-right)
2. Nhập câu hỏi (VD: "sách về lập trình python")
3. Frontend POST /chat với message
4. Backend:
   ├─ Query ChromaDB (vector search trên book data)
   ├─ Lấy top relevant books
   ├─ Gửi context + user message đến Gemini API
   └─ Trả về AI response
5. Frontend hiển thị reply
6. Lưu chat history vào localStorage (max 100 messages)
```

---

## 3. CẤU TRÚC THƯ MỤC

```
Lib_Web/
├── app.py                    # Entry point, khởi tạo Flask app
├── config.py                 # Configuration (DB, upload, session)
├── models.py                 # SQLAlchemy models
├── decorators.py             # @admin_required, @login_required
├── email_service.py          # Email sending (SMTP)
├── phone_service.py          # SMS sending (Twilio) [optional]
├── requirements.txt          # Python dependencies
├── Procfile                  # For deployment (Heroku/Render)
├── .env                      # Environment variables (SECRET!)
├── .env.example              # Template for .env
│
├── routes/                   # Blueprint routes
│   ├── main.py               # Homepage, books list, category
│   ├── auth.py               # Login, register, logout, email verify
│   ├── book.py               # Book detail, borrow
│   ├── user.py               # Profile, borrows history
│   ├── admin.py              # Admin dashboard, manage books/users/borrows
│   ├── notification.py       # Notification API
│   ├── chatbot.py            # Chatbot API
│   └── google_oauth.py       # Google OAuth login
│
├── templates/
│   ├── user/                 # User-facing templates
│   │   ├── base.html         # Layout with navbar, notification bell
│   │   ├── home.html         # Homepage with carousel
│   │   ├── books.html        # Books list with search
│   │   ├── book_detail.html  # Book detail with borrow modal
│   │   ├── borrows.html      # Borrow history
│   │   └── profile.html      # User profile
│   ├── auth/                 # Authentication templates
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── verify_email.html
│   │   ├── forgot_password.html
│   │   └── reset_password.html
│   └── admin/                # Admin templates
│       ├── base.html         # Admin layout with sidebar
│       ├── dashboard.html    # Statistics
│       ├── books.html        # Manage books
│       ├── users.html        # Manage users
│       ├── borrows.html      # Manage borrow requests
│       ├── add_book.html     # Add new book
│       └── edit_book.html    # Edit book
│
├── static/
│   ├── style.css             # Global styles
│   ├── css/
│   │   └── chatbot.css       # Chatbot UI styles
│   ├── js/
│   │   ├── main.js           # AJAX borrow, toast, password toggle
│   │   └── chatbot.js        # Chatbot logic, chat history
│   └── uploads/              # User avatars, book covers
│
├── chroma_db/                # ChromaDB vector database
└── DOCS/                     # Documentation
    └── GHI_CHU.md            # This file
```

---

## 4. CHI TIẾT CÁC FILE CHÍNH

### 📄 `app.py`
**Mục đích:** Entry point, khởi tạo Flask app

**Chức năng:**
- Tạo Flask app từ `config.py`
- Khởi tạo database (`db.create_all()`)
- Đăng ký blueprints: `main_bp`, `auth_bp`, `book_bp`, `user_bp`, `admin_bp`, `notification_bp`, `chatbot_bp`
- Set `SECRET_KEY` và `SESSION_COOKIE_NAME` dựa trên port (tránh conflict khi run nhiều instance)
- Error handler cho `RequestEntityTooLarge` (file upload quá lớn)

**Chạy:**
```bash
python3.10 app.py        # Run on port 8000
python3.10 app.py 8001   # Run on port 8001
```

---

### 📄 `config.py`
**Mục đích:** Cấu hình Flask app

**Nội dung:**
- `SQLALCHEMY_DATABASE_URI`: MySQL connection string
- `UPLOAD_FOLDER`: Thư mục lưu file upload
- `ALLOWED_EXTENSIONS`: File extensions cho phép
- `MAX_CONTENT_LENGTH`: Giới hạn kích thước upload (2MB)
- `CATEGORY_MAP`: Map slug → display name cho danh mục sách
- `allowed_file(filename)`: Helper check file extension

---

### 📄 `models.py`
**Mục đích:** SQLAlchemy ORM models

**Models:**

#### 1. **User**
```python
- id: Primary key
- username: Tên hiển thị
- student_staff_id: MSSV/MSCB (UNIQUE, login)
- email: Email (UNIQUE, verify)
- phone: Phone number (UNIQUE, optional)
- password_hash: Bcrypt hashed password
- is_admin: Boolean
- role: user/admin/librarian
- avatar_url: Path to avatar image
- is_email_verified: Boolean
- email_verification_code: OTP code
```

#### 2. **Book**
```python
- id: Primary key
- title: Tên sách
- author: Tác giả
- category: am_nhac/lap_trinh/truyen_tranh/y_hoc/tam_ly
- image_url: Path to book cover
- quantity: Tổng số lượng
- available_quantity: Số lượng còn lại
- is_active: Boolean (soft delete)
- views_count: Lượt xem
```

#### 3. **Borrow**
```python
- id: Primary key
- user_id: FK → User
- book_id: FK → Book
- borrow_date: Ngày mượn
- expected_return_date: Ngày trả dự kiến
- return_date: Ngày trả thực tế (NULL nếu chưa trả)
- status: pending/approved/rejected
- approved_by: FK → User (admin)
- approved_at: Timestamp
- book_title: Snapshot tên sách
- return_condition: good/damaged/lost
- return_notes: Ghi chú khi trả
```

#### 4. **Notification**
```python
- id: Primary key
- recipient_id: FK → User
- message: Nội dung thông báo
- link: URL redirect khi click
- is_read: Boolean
- type: info/success/warning/error
- created_at: Timestamp
```

#### 5. **Audit**
```python
- id: Primary key
- action: approve_borrow/reject_borrow/create_book/delete_user...
- actor_user_id: FK → User (người thực hiện)
- target_borrow_id: FK → Borrow (nếu liên quan)
- target_book_id: FK → Book (nếu liên quan)
- details: JSON metadata
- timestamp: Timestamp
```

---

### 📄 `routes/main.py`
**Blueprint:** `main_bp`

**Routes:**
- `GET /` → `index()`: Homepage (popular + latest books)
- `GET /books` → `books()`: Danh sách sách (search + pagination)
- `GET /category/<slug>` → `category()`: Lọc theo danh mục
- `GET /_suggest_books` → Autocomplete search (AJAX)

---

### 📄 `routes/auth.py`
**Blueprint:** `auth_bp`

**Routes:**
- `GET/POST /auth/login` → Đăng nhập
- `GET /auth/logout` → Đăng xuất
- `GET/POST /auth/register` → Đăng ký
- `GET/POST /auth/verify-email` → Xác thực email (OTP)
- `GET/POST /auth/forgot-password` → Quên mật khẩu
- `GET/POST /auth/reset-password` → Đặt lại mật khẩu

**Logic:**
- Login: Tìm user theo `student_staff_id` HOẶC `email`, verify password
- Register: Validate, hash password, tạo OTP, gửi email
- Email verify: Check OTP, set `is_email_verified = True`

---

### 📄 `routes/book.py`
**Blueprint:** `book_bp`

**Routes:**
- `GET /book/book/<book_id>` → `detail()`: Chi tiết sách
- `POST /book/borrow/<book_id>` → `borrow()`: Mượn sách (form submission)

**Logic mượn sách:**
```python
1. Check user đã đăng nhập
2. Check duplicate borrow (pending/approved cho cùng book)
3. Tạo Borrow record với status=PENDING
4. GỬI NOTIFICATION cho ALL admins
5. GỬI EMAIL xác nhận cho user
6. Redirect về homepage với flash message
```

---

### 📄 `routes/admin.py`
**Blueprint:** `admin_bp` (require `@admin_required`)

**Routes:**
- `GET /admin/` → `dashboard()`: Thống kê
- `GET /admin/books` → `books()`: Quản lý sách
- `GET /admin/users` → `users()`: Quản lý users
- `GET /admin/borrows` → `borrows()`: Quản lý yêu cầu mượn
- `POST /admin/approve/<borrow_id>` → Duyệt yêu cầu
- `POST /admin/reject/<borrow_id>` → Từ chối yêu cầu
- `POST /admin/books/add` → Thêm sách mới
- `POST /admin/books/edit/<book_id>` → Sửa sách
- `POST /admin/books/delete/<book_id>` → Xóa sách

**Logic approve borrow:**
```python
1. Tìm Borrow theo ID, check status=pending
2. Giảm available_quantity của Book
3. Update Borrow: status=approved, approved_by, approved_at
4. Tạo Audit log
5. GỬI EMAIL thông báo approved
6. GỬI NOTIFICATION cho user
7. Commit transaction
```

---

### 📄 `routes/notification.py`
**Blueprint:** `notification_bp`

**Routes:**
- `GET /notification/notifications` → Lấy danh sách notifications (JSON)
- `POST /notification/notifications/mark-read/<id>` → Đánh dấu đã đọc
- `POST /notification/notifications/mark-all-read` → Đánh dấu tất cả đã đọc

**Response format:**
```json
{
  "success": true,
  "notifications": [
    {
      "id": 1,
      "message": "Yêu cầu mượn sách đã được duyệt",
      "link": "/user/borrows",
      "is_read": false,
      "type": "success",
      "created_at": "2025-12-05 10:30:00"
    }
  ],
  "unread_count": 1
}
```

---

### 📄 `routes/chatbot.py`
**Blueprint:** `chatbot_bp`

**Route:**
- `POST /chat` → `chat()`: Xử lý chat message

**Logic:**
```python
1. Nhận message từ user
2. Query ChromaDB (vector search) → lấy top 5 relevant books
3. Build context từ book results
4. Gửi context + user message tới Gemini API
5. Nhận AI response
6. Return JSON: {"reply": "..."}
```

---

### 📄 `static/js/main.js`
**Mục đích:** Client-side interactions

**Chức năng:**
1. **AJAX Borrow** (deprecated, giờ dùng form modal)
2. **Toast notifications** - `showToast(type, title, message)`
3. **Password toggle** - Show/Hide password input
4. **Search autocomplete** - Gợi ý sách khi gõ

---

### 📄 `static/js/chatbot.js`
**Mục đích:** Chatbot UI & logic

**Chức năng:**
1. **UI Management:**
   - Floating button (bottom-right)
   - Chat box toggle
   - Message rendering

2. **Chat Logic:**
   - Submit message → POST /chat
   - Loading indicator (typing animation)
   - Append bot reply

3. **History Management:**
   - Save chat history to localStorage
   - Load history on page load
   - Clear history button
   - Max 100 messages

---

## 5. DATABASE MODELS

### ERD (Simplified)
```
User (1) ──── (N) Borrow (N) ──── (1) Book
  │                  │
  │                  │
  └─(1)──(N) Notification
  │
  └─(1)──(N) Audit
```

### Quan hệ:
- 1 User có nhiều Borrow
- 1 Book có nhiều Borrow
- 1 User có nhiều Notification
- 1 User (admin) có nhiều Audit actions

---

## 6. GỢI Ý CẢI TIẾN

### 🔹 Security
- [ ] Thêm CSRF protection (Flask-WTF)
- [ ] Rate limiting cho login/register
- [ ] SQL injection prevention (đã dùng ORM, nhưng cần check raw queries)
- [ ] XSS protection (escape user input)

### 🔹 Performance
- [ ] Cache popular/latest books (Redis)
- [ ] Optimize database queries (add indexes)
- [ ] CDN cho static files
- [ ] Pagination cho admin views

### 🔹 UX
- [ ] Real-time notifications (WebSocket thay vì polling)
- [ ] Email templates với HTML (đẹp hơn)
- [ ] Push notifications (PWA)
- [ ] Dark mode

### 🔹 Code Quality
- [ ] Dùng Flask-Migrate cho database migrations
- [ ] Unit tests (pytest)
- [ ] API documentation (Swagger)
- [ ] Environment-based config (dev/staging/prod)

### 🔹 Features
- [ ] Đánh giá & review sách
- [ ] Wishlist
- [ ] Gia hạn mượn sách
- [ ] Phạt trễ hạn
- [ ] Export reports (Excel/PDF)

---

## 📞 SUPPORT

**Email:** quochuyphan2k5@gmail.com  
**Phone:** 0917715034

---

**Ngày cập nhật:** 2025-12-05  
**Phiên bản:** 2.0 (Với borrow approval system & notifications)
