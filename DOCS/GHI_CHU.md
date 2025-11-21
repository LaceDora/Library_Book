GHI CHÚ CHUNG DỰ ÁN - Thư viện Python
===================================

Tài liệu tóm tắt chức năng chính và ghi chú cho từng file trong workspace.
Nội dung bằng tiếng Việt.

---

1) app.py
-----------
Mục đích:
- Khởi tạo runtime cho Flask app, cấu hình upload limit (2MB), xử lý lỗi RequestEntityTooLarge.
- Khởi tạo DB (db.create_all()) và gọi `remove_username_unique_constraint()` để loại bỏ ràng buộc UNIQUE trên username nếu cần.
- Đăng ký blueprints: main, auth, book, user, admin.
- Trong __main__: tạo secret_key và SESSION_COOKIE_NAME tùy theo port để tránh xung đột session khi chạy nhiều instance.

Gợi ý:
- Kiểm tra `app.register_blueprint(..., name='...')` nếu gặp lỗi; thông thường chỉ cần `app.register_blueprint(bp, url_prefix=...)`.
- Việc set secret_key mới mỗi lần khởi chạy thích hợp cho dev; production cần secret cố định (env var).

---

2) config.py
-------------
Mục đích:
- Tạo Flask app instance và cấu hình session, upload (UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH).
- Thiết lập SQLALCHEMY_DATABASE_URI (hiện dùng MySQL) và engine options.
- CATEGORY_MAP: map slug -> tên hiển thị cho category.
- Hàm helper `allowed_file(filename)` để kiểm tra extension.

Gợi ý:
- Đặt DB URI, SECRET KEY, và các config nhạy cảm bằng biến môi trường.
- Dùng Flask-Migrate để quản lý schema production.

---

3) models.py
------------
Model chính:
- User: id, username (không unique), password_hash, is_admin, student_staff_id (unique), role, avatar_url, email (unique), phone (unique).
- Book: id, title, author, image_url, quantity, category, is_active, views_count.
- Borrow: id, user_id, book_id, borrow_date, book_title (snapshot), return_date, return_condition, return_notes.
- Audit: id, action, actor_user_id, target_borrow_id, target_book_id, timestamp, details.

Hàm:
- remove_username_unique_constraint(): cố gắng xóa ràng buộc unique của username (ALTER TABLE). Thao tác schema runtime, nên dùng migration.

Gợi ý:
- Kiểm tra behavior của các cột unique (email/phone) khi NULL trong MySQL.
- Dùng migration tool cho thay đổi schema lớn.

---

4) decorators.py
-----------------
- admin_required: decorator kiểm tra session:
  - Nếu không có `user_id` -> redirect tới login.
  - Nếu không có `is_admin` -> redirect về trang chính.

Gợi ý: có thể tách `login_required` chung và dùng `admin_required` chỉ bổ sung quyền admin.

---

5) routes/main.py
------------------
- index(): Hiển thị trang chủ, lấy `popular` và `latest` (limit 8).
- books(): Danh sách sách, hỗ trợ search (title hoặc author) và paginate (per_page=9).
- category(slug): Lọc theo category; slug -> display name via CATEGORY_MAP.

Gợi ý:
- Nếu cần điều kiện OR phức tạp hơn, dùng `from sqlalchemy import or_`.

---

6) routes/auth.py
------------------
- login(): Đăng nhập bằng `student_staff_id` (form field name là `login`) và password; lưu session: user_id, is_admin, username, role.
- logout(): Xóa session.
- register(): Kiểm tra password confirm; kiểm tra trùng MSSV/MSCB; tạo user với password hash.

Gợi ý:
- Validate mật khẩu mạnh, email format (nếu dùng), xử lý lỗi DB với rollback.

---

7) routes/book.py
------------------
- detail(book_id): Hiển thị chi tiết sách và tăng `views_count`.
- borrow(book_id): Mượn sách theo cách thông thường (redirect), giảm quantity và tạo Borrow.
- borrow_ajax(book_id): Xử lý mượn qua AJAX, trả JSON {success, message, new_quantity, ...}. Kiểm tra header 'X-Requested-With'.
- return_book(borrow_id): Xử lý trả sách (user hoặc admin), cập nhật return_date và tăng quantity nếu phù hợp, tạo Audit.

Gợi ý:
- Bọc thao tác giảm/increase quantity + tạo borrow trong transaction để tránh race condition.
- borrow_ajax nên trả error mã phù hợp và JSON rõ ràng.

---

8) routes/user.py
------------------
- profile(): Xem/cập nhật profile, upload avatar (kiểm tra extension + kích thước), đổi mật khẩu (yêu cầu mật khẩu hiện tại).
- borrows(): Danh sách lịch sử mượn của user hiện tại.
- list_users()/history()/delete(user_id): Các hàm admin để quản lý user, xem lịch sử và xóa user (khi xóa sẽ phục hồi quantity nếu có borrows chưa trả).

Gợi ý:
- Khi xóa user, đảm bảo ghi Audit và xử lý rollback nếu có lỗi.
- Upload avatar: sanitize filename, lưu vào `static/uploads`.

---

9) routes/admin.py
-------------------
- dashboard(): Thống kê tổng quan (tổng sách, tổng user, borrows active, recent audit logs).
- books(): Quản lý sách (search, paginate, per_page=10).
- users(): Quản lý người dùng (search, paginate).
- update_user_role(user_id): POST thay đổi role (không cho phép thay đổi chính mình hoặc admin).
- borrows(): Danh sách borrow cho admin (filter user/book/status).
- add_book(), edit_book(), delete_book(): CRUD sách cho admin.
- delete_user(user_id): Xóa user (cùng lịch sử) — chỉ admin.
- user_history(user_id): Xem lịch sử mượn 1 user.
- return_book(borrow_id): Admin xác nhận trả sách, có thể kèm tình trạng (good/damaged/lost).

Gợi ý:
- Kiểm tra quyền kỹ, và log hành động admin vào Audit.

---

10) Templates (tổng hợp)
-------------------------
- `templates/base.html`: layout chính (navbar, flash, toast, chèn `static/js/main.js`).
  - Meta `user-logged-in` được thêm nếu session có user_id.
- `templates/admin/base.html`: layout admin (navbar + sidebar).
- `templates/home.html`: hero + popular carousel + latest grid.
- `templates/books.html`: danh sách/paging/search; nút mượn có class `borrow-btn` và id `book-qty-<id>` để JS cập nhật.
- `templates/book_detail.html`: chi tiết sách, hiện số lượng và nút mượn.
- `templates/login.html`, `templates/register.html`: auth forms.
- `templates/profile.html`: upload avatar + đổi mật khẩu.
- `templates/borrows.html`: lịch sử mượn user-facing.
- `templates/admin/*`: admin views (books, borrows, users, add/edit forms, history).

Gợi ý:
- Các template có nhiều inline JS/CSS; cân nhắc tách ra file tĩnh để dễ bảo trì.
- Xác nhận CSRF nếu dùng forms quan trọng (Flask-WTF) để tăng an toàn.

---

11) static/js/main.js
----------------------
- Lắng nghe event `.borrow-btn` để gửi POST tới `/book/borrow_ajax/<id>`.
- Nếu không logged-in (meta user-logged-in không có), redirect tới login.
- Cập nhật số lượng sách hiển thị và thay đổi trạng thái nút sau khi mượn.
- showToast(type, title, message): helper tạo Bootstrap toast và xóa sau khi ẩn.

Gợi ý:
- Nếu có CSRF token, thêm vào header.
- Thay vì tạo container mới mỗi lần, có thể reuse một container global để tránh DOM clutter.

---

12) static/style.css
---------------------
- Chứa nhiều style chung cho giao diện, auth pages, carousel, layout.

Gợi ý:
- Tách style admin nếu cần.

---

GỢI Ý CẢI TIẾN CHUNG
---------------------
- Dùng Flask-Migrate/Alembic cho quản lý migration thay vì gọi `db.create_all()` và ALTER TABLE runtime.
- Sử dụng biến môi trường cho SECRET_KEY và DATABASE_URI.
- Thêm CSRF protection (Flask-WTF) cho các POST form.
- Xử lý concurrency khi mượn sách (optimistic locking hoặc SELECT FOR UPDATE) để tránh quantity âm khi nhiều người mượn cùng lúc.
- Thêm tests đơn vị cho các flow mượn/trả/xóa user.

---

Nếu bạn muốn, tôi có thể:
- Chèn comment trực tiếp sâu hơn vào từng hàm (tôi đã thêm header + chú thích cơ bản vào file); hoặc
- Viết tài liệu chi tiết hơn (per-function, per-parameter) vào file `DOCS/GHI_CHU.md` (có thể mở rộng).

Hoàn tất: chỉnh sửa đã thêm các chú thích cơ bản vào mã nguồn và tạo file này.
