"""routes/admin.py

Blueprint cho các chức năng quản trị (admin):
 - dashboard: thống kê nhanh
 - books: quản lý sách (thêm/sửa/ẩn)
 - users: quản lý người dùng (tìm kiếm, thay đổi vai trò, xóa)
 - borrows: xem và xử lý lịch sử mượn (admin có thể đánh dấu trả sách)

Ghi chú: tất cả route admin đều dùng decorator `@admin_required` để bảo đảm quyền truy cập.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Book, Borrow, Audit, Notification
from decorators import admin_required
from config import CATEGORY_MAP, LOAN_PERIOD_DAYS
from datetime import datetime, timedelta
from email_service import send_borrow_approved_email, send_borrow_rejected_email
import re

admin = Blueprint('admin_bp', __name__)

@admin.route('/')
@admin_required
def dashboard():
    total_books = Book.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    active_borrows = Borrow.query.filter_by(return_date=None).count()
    total_borrows = Borrow.query.count()
    recent_activities = Audit.query.order_by(Audit.timestamp.desc()).limit(10).all()

    # Prepare display versions of the activity details: replace user IDs with usernames when possible
    recent_activities_display = []
    user_ref_pattern = re.compile(r"\b(User|user|Admin|admin|Người dùng|người dùng)\s+(\d+)\b")

    for a in recent_activities:
        details = a.details or ''

        def _replace_user(match):
            label = match.group(1)
            uid = match.group(2)
            try:
                u = User.query.get(int(uid))
            except Exception:
                u = None
            if u:
                return f"{label} {u.username}"
            return match.group(0)

        display_details = user_ref_pattern.sub(_replace_user, details)

        recent_activities_display.append({
            'timestamp': a.timestamp,
            'action': a.action,
            'details': display_details
        })

    return render_template('admin/dashboard.html',
                         total_books=total_books,
                         total_users=total_users,
                         active_borrows=active_borrows,
                         total_borrows=total_borrows,
                         recent_activities=recent_activities_display)

@admin.route('/books')
@admin_required
def books():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Book.query
    
    if search:
        query = query.filter(Book.title.like(f'%{search}%') | Book.author.like(f'%{search}%'))
    
    books = query.order_by(Book.id.desc()).paginate(page=page, per_page=10)
    return render_template('admin/books.html', books=books)

@admin.route('/users')
@admin_required
def users():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = User.query.filter_by(is_admin=False)
    
    if search:
        query = query.filter(User.username.like(f'%{search}%'))
    
    users = query.order_by(User.id.desc()).paginate(page=page, per_page=10)
    return render_template('admin/users.html', users=users)


@admin.route('/users/role/<int:user_id>', methods=['POST'])
@admin_required
def update_user_role(user_id):
    # Prevent changing own role to avoid accidental lockout and prevent changing admin's role
    if session.get('user_id') == user_id:
        flash('Không thể thay đổi vai trò của chính mình.', 'danger')
        return redirect(url_for('admin_bp.users'))

    user = User.query.get_or_404(user_id)
    # Do not allow editing role of admin accounts via this UI
    if user.is_admin:
        flash('Không thể thay đổi vai trò của tài khoản admin.', 'danger')
        return redirect(url_for('admin_bp.users'))

    role = request.form.get('role')
    if role not in ['student', 'lecturer', 'staff']:
        flash('Vai trò không hợp lệ.', 'danger')
        return redirect(url_for('admin_bp.users'))

    user.role = role
    db.session.commit()
    flash('Đã cập nhật vai trò người dùng.', 'success')
    return redirect(url_for('admin_bp.users'))


@admin.route('/users/toggle-active/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Admin bật/tắt trạng thái is_active của user."""
    if session.get('user_id') == user_id:
        flash('Không thể thay đổi trạng thái của chính mình.', 'danger')
        return redirect(url_for('admin_bp.users'))

    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Không thể thay đổi trạng thái tài khoản admin.', 'danger')
        return redirect(url_for('admin_bp.users'))

    # Toggle
    user.is_active = not bool(user.is_active)

    # Add audit log
    action = 'unlock_user' if user.is_active else 'lock_user'
    audit = Audit(
        action=action,
        actor_user_id=session.get('user_id'),
        target_borrow_id=None,
        target_book_id=None,
        details=f'Admin {session.get("user_id")} set is_active={user.is_active} for user {user.id}'
    )
    db.session.add(audit)
    db.session.commit()

    flash('Đã cập nhật trạng thái tài khoản.', 'success')
    return redirect(url_for('admin_bp.users'))

@admin.route('/borrows')
@admin_required
def borrows():
    page = request.args.get('page', 1, type=int)
    user_filter = request.args.get('user', '')
    book_filter = request.args.get('book', '')
    status = request.args.get('status', '')
    
    # Query with explicit joins and select all needed columns
    query = db.session.query(Borrow, User, Book).join(User, Borrow.user_id == User.id).join(Book, Borrow.book_id == Book.id)
    
    if user_filter:
        query = query.filter(User.username.like(f'%{user_filter}%'))
    if book_filter:
        query = query.filter(Book.title.like(f'%{book_filter}%'))
    if status == 'pending':
        query = query.filter(Borrow.status == 'pending')
    elif status == 'borrowing':
        query = query.filter(Borrow.status == 'approved', Borrow.return_date == None)
    elif status == 'returned':
        query = query.filter(Borrow.return_date != None)
    
    pagination = query.order_by(Borrow.borrow_date.desc()).paginate(page=page, per_page=10)
    
    # Transform results to include user and book objects
    borrows_with_relations = []
    for borrow, user, book in pagination.items:
        borrow.user = user
        borrow.book = book
        borrows_with_relations.append(borrow)
    
    # Create a new pagination object with transformed items
    class BorrowPagination:
        def __init__(self, items, page, pages, total, has_prev, has_next, prev_num, next_num):
            self.items = items
            self.page = page
            self.pages = pages
            self.total = total
            self.has_prev = has_prev
            self.has_next = has_next
            self.prev_num = prev_num
            self.next_num = next_num
    
    borrows = BorrowPagination(
        items=borrows_with_relations,
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
        has_prev=pagination.has_prev,
        has_next=pagination.has_next,
        prev_num=pagination.prev_num,
        next_num=pagination.next_num
    )
    
    return render_template('admin/borrows.html', borrows=borrows, timedelta=timedelta)

@admin.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        category = request.form.get('category')
        quantity = int(request.form.get('quantity', 1))
        image_url = request.form.get('image_url')
        
        book = Book(title=title, author=author, category=category,
                   quantity=quantity, available_quantity=quantity, image_url=image_url)
        db.session.add(book)
        db.session.commit()
        
        flash('Thêm sách mới thành công!', 'success')
        return redirect(url_for('admin_bp.books'))
        
    return render_template('admin/add_book.html', categories=CATEGORY_MAP.values())

@admin.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.category = request.form.get('category')
        new_quantity = int(request.form.get('quantity', 1))
        # Cập nhật cả quantity và available_quantity (giả sử admin nhập lại số lượng ban đầu)
        book.quantity = new_quantity
        book.available_quantity = new_quantity
        book.image_url = request.form.get('image_url')
        book.is_active = bool(request.form.get('is_active'))
        # Lưu mô tả sách nếu có
        if hasattr(book, 'description'):
            book.description = request.form.get('description')
        db.session.commit()
        flash('Cập nhật sách thành công!', 'success')
        return redirect(url_for('admin_bp.books'))
    return render_template('admin/edit_book.html', book=book, categories=CATEGORY_MAP.values())

@admin.route('/books/delete/<int:book_id>')
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_active = False
    db.session.commit()
    flash('Đã ẩn sách khỏi thư viện.', 'success')
    return redirect(url_for('admin_bp.books'))

@admin.route('/users/delete/<int:user_id>')
@admin_required
def delete_user(user_id):
    if session.get('user_id') == user_id:
        flash('Không thể xóa tài khoản của chính mình.', 'danger')
        return redirect(url_for('admin_bp.users'))
        
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Không thể xóa tài khoản admin.', 'danger')
        return redirect(url_for('admin_bp.users'))
        
    # Process user's borrows
    borrows = Borrow.query.filter_by(user_id=user_id).all()
    for borrow in borrows:
        if not borrow.return_date:
            book = Book.query.get(borrow.book_id)
            if book:
                book.quantity += 1
        db.session.delete(borrow)
    
    db.session.delete(user)
    db.session.commit()
    flash('Đã xóa người dùng và lịch sử mượn sách của họ.', 'success')
    return redirect(url_for('admin_bp.users'))

@admin.route('/users/history/<int:user_id>')
@admin_required
def user_history(user_id):
    user = User.query.get_or_404(user_id)
    borrows = Borrow.query.filter_by(user_id=user_id).order_by(Borrow.borrow_date.desc()).all()
    has_unreturned_books = any(not borrow.return_date for borrow in borrows)
    
    return render_template('admin/user_history.html', 
                         user=user, 
                         borrows=borrows, 
                         has_unreturned_books=has_unreturned_books)

@admin.route('/borrows/return/<int:borrow_id>', methods=['POST'])
@admin_required
def return_book(borrow_id):
    borrow = Borrow.query.get_or_404(borrow_id)
    if not borrow.return_date:
        book_condition = request.form.get('book_condition')
        return_notes = request.form.get('return_notes')
        
        if book_condition not in ['good', 'damaged', 'lost']:
            flash('Tình trạng sách không hợp lệ!', 'danger')
            return redirect(url_for('admin_bp.user_history', user_id=borrow.user_id))
        
        borrow.return_date = datetime.now()
        borrow.return_condition = book_condition
        borrow.return_notes = return_notes
        # Clear any pending return request flag
        borrow.return_requested = False
        borrow.return_requested_at = None
        
        book = Book.query.get(borrow.book_id)
        if book and book_condition != 'lost':
            book.available_quantity += 1
            
        condition_text = {
            'good': 'tốt',
            'damaged': 'hư hỏng nhẹ',
            'lost': 'mất sách'
        }
        audit_details = f'Admin {session.get("user_id")} đánh dấu trả sách (ID: {borrow.id}). ' \
                       f'Tình trạng: {condition_text[book_condition]}'
        if return_notes:
            audit_details += f'. Ghi chú: {return_notes}'
            
        audit = Audit(
            action='return',
            actor_user_id=session.get('user_id'),
            target_borrow_id=borrow.id,
            target_book_id=borrow.book_id,
            details=audit_details
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('Đã ghi nhận trả sách thành công!', 'success')
    return redirect(url_for('admin_bp.user_history', user_id=borrow.user_id))

@admin.route('/users/<int:user_id>/update-student-id', methods=['POST'])
@admin_required
def update_student_id(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Không thể chỉnh sửa thông tin của admin!', 'danger')
        return redirect(url_for('admin_bp.users'))
        
    new_id = request.form.get('student_staff_id', '').strip()
    
    # Validate input
    if not new_id or not new_id.isdigit() or len(new_id) < 7 or len(new_id) > 10:
        flash('MSSV/MSCB không hợp lệ! Yêu cầu 7-10 ký tự số.', 'danger')
        return redirect(url_for('admin_bp.users'))
        
    # Check if ID already exists
    existing_user = User.query.filter(User.student_staff_id == new_id, User.id != user_id).first()
    if existing_user:
        flash('MSSV/MSCB đã tồn tại!', 'danger')
        return redirect(url_for('admin_bp.users'))
    
    # Update user
    old_id = user.student_staff_id
    user.student_staff_id = new_id
    
    # Add audit log
    audit = Audit(
        action='update_student_id',
        actor_user_id=session['user_id'],
        target_borrow_id=None,
        target_book_id=None,
        details=f'Admin {session["user_id"]} cập nhật MSSV/MSCB của user {user.id} từ {old_id} thành {new_id}'
    )
    
    db.session.add(audit)
    db.session.commit()
    
    flash(f'Đã cập nhật MSSV/MSCB cho người dùng {user.username}!', 'success')
    return redirect(url_for('admin_bp.users'))

@admin.route('/borrows/approve/<int:borrow_id>', methods=['POST'])
@admin_required
def approve_borrow(borrow_id):
    """Admin duyệt yêu cầu mượn sách"""
    borrow = Borrow.query.get_or_404(borrow_id)
    
    if borrow.status != 'pending':
        flash('Yêu cầu này đã được xử lý trước đó.', 'warning')
        return redirect(url_for('admin_bp.borrows'))
    
    book = Book.query.get(borrow.book_id)
    if not book:
        flash('Không tìm thấy sách.', 'danger')
        return redirect(url_for('admin_bp.borrows'))
    
    if book.available_quantity <= 0:
        flash('Sách đã hết, không thể duyệt yêu cầu này.', 'danger')
        return redirect(url_for('admin_bp.borrows'))
    
    # Approve the borrow request
    borrow.status = 'approved'
    borrow.approved_by = session.get('user_id')
    borrow.approved_at = datetime.now()
    book.available_quantity -= 1
    
    # Add audit log
    audit = Audit(
        action='approve_borrow',
        actor_user_id=session.get('user_id'),
        target_borrow_id=borrow.id,
        target_book_id=borrow.book_id,
        details=f'Admin {session.get("user_id")} duyệt yêu cầu mượn sách ID {borrow.id}'
    )
    db.session.add(audit)
    db.session.commit()
    
    # Send approval email to user
    try:
        user = User.query.get(borrow.user_id)
        if user:
            # Create notification
            notification = Notification(
                user_id=user.id,
                message=f"Yêu cầu mượn sách '{book.title}' của bạn đã được duyệt!",
                link=url_for('user_bp.borrows'),
                type='success'
            )
            db.session.add(notification)
            db.session.commit()

            if user.email:
                # Use stored expected_return_date
                return_deadline = borrow.expected_return_date if borrow.expected_return_date else (borrow.borrow_date + timedelta(days=LOAN_PERIOD_DAYS))
                send_borrow_approved_email(
                    user.email, 
                    user.username, 
                    book.title, 
                    book.author, 
                    borrow.borrow_date, 
                    return_deadline
                )
    except Exception as e:
        print(f"Lỗi gửi email/notification duyệt: {e}")
    
    flash('Đã duyệt yêu cầu mượn sách thành công!', 'success')
    return redirect(url_for('admin_bp.borrows'))

@admin.route('/borrows/reject/<int:borrow_id>', methods=['POST'])
@admin_required
def reject_borrow(borrow_id):
    """Admin từ chối yêu cầu mượn sách"""
    borrow = Borrow.query.get_or_404(borrow_id)
    
    if borrow.status != 'pending':
        flash('Yêu cầu này đã được xử lý trước đó.', 'warning')
        return redirect(url_for('admin_bp.borrows'))
    
    # Reject the borrow request
    borrow.status = 'rejected'
    
    # Add audit log
    audit = Audit(
        action='reject_borrow',
        actor_user_id=session.get('user_id'),
        target_borrow_id=borrow.id,
        target_book_id=borrow.book_id,
        details=f'Admin {session.get("user_id")} từ chối yêu cầu mượn sách ID {borrow.id}'
    )
    db.session.add(audit)
    db.session.commit()
    
    # Send rejection email to user
    try:
        user = User.query.get(borrow.user_id)
        book = Book.query.get(borrow.book_id)
        if user and book:
            # Create notification
            notification = Notification(
                user_id=user.id,
                message=f"Yêu cầu mượn sách '{book.title}' của bạn đã bị từ chối.",
                link=url_for('user_bp.borrows'),
                type='error'
            )
            db.session.add(notification)
            db.session.commit()

            if user.email:
                send_borrow_rejected_email(
                    user.email, 
                    user.username, 
                    book.title, 
                    book.author
                )
    except Exception as e:
        print(f"Lỗi gửi email/notification từ chối: {e}")
    
    flash('Đã từ chối yêu cầu mượn sách.', 'info')
    return redirect(url_for('admin_bp.borrows'))
