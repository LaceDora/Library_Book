"""routes/book.py

Chứa các route xử lý thao tác liên quan tới sách:
 - detail: xem chi tiết sách và tăng lượt xem
 - borrow: mượn sách (điều hướng thông thường)
 - borrow_ajax: mượn sách qua AJAX (trả về JSON)
 - return_book: xử lý trả sách (user hoặc admin)

Lưu ý:
 - Các thao tác thay đổi số lượng sách cần thực hiện trong transaction và xử lý rollback khi có lỗi.
 - borrow_ajax trả JSON để JS phía client cập nhật giao diện không cần reload.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from models import db, Book, Borrow, Audit

book = Blueprint('book', __name__)

@book.route('/book/<int:book_id>')
def detail(book_id):
    """Trang chi tiết một cuốn sách."""
    book = Book.query.get_or_404(book_id)

    # Tăng lượt xem
    try:
        book.views_count = (book.views_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Lấy sách liên quan (cùng thể loại, trừ cuốn hiện tại)
    related_books = Book.query.filter(
        Book.category == book.category,
        Book.id != book.id,
        Book.is_active == True
    ).order_by(Book.views_count.desc()).limit(4).all()

    prev_url = request.referrer or url_for('main_bp.books')
    return render_template('book_detail.html', book=book, prev_url=prev_url, related_books=related_books)

@book.route("/borrow/<int:book_id>")
def borrow(book_id):
    if not session.get("user_id"):
        flash("Hãy đăng nhập để mượn sách!", "warning")
        return redirect(url_for("auth_bp.login"))
    book = Book.query.get_or_404(book_id)
    if book.available_quantity > 0:
        borrow = Borrow(user_id=session["user_id"], book_id=book.id, book_title=book.title, borrow_date=datetime.now())
        book.available_quantity -= 1
        db.session.add(borrow)
        db.session.commit()
        flash("Đã mượn sách thành công!", "success")
    else:
        flash("Sách đã hết!", "danger")
    next_url = request.args.get('next') or request.referrer
    if not next_url:
        return redirect(url_for('main_bp.books'))
    return redirect(next_url)

@book.route('/borrow_ajax/<int:book_id>', methods=['POST'])
def borrow_ajax(book_id):
    # Kiểm tra AJAX request
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Yêu cầu không hợp lệ.'}), 400
        
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Vui lòng đăng nhập để mượn sách.'}), 401

    try:
        book = Book.query.get(book_id)
        if not book or not book.is_active:
            return jsonify({
                'success': False, 
                'message': 'Sách không tồn tại hoặc đã bị vô hiệu hóa.',
                'new_quantity': 0
            }), 404

        # Kiểm tra số lượng có sẵn
        if book.available_quantity is None or book.available_quantity <= 0:
            return jsonify({
                'success': False, 
                'message': 'Sách đã hết, vui lòng chọn sách khác.',
                'new_quantity': 0
            }), 400

        # Kiểm tra xem người dùng có đang mượn sách này không
        existing_borrow = Borrow.query.filter_by(
            user_id=session['user_id'],
            book_id=book.id,
            return_date=None
        ).first()
        
        if existing_borrow:
            return jsonify({
                'success': False, 
                'message': 'Bạn đang mượn cuốn sách này. Vui lòng trả sách trước khi mượn lại.',
                'new_quantity': book.available_quantity,
                'error_type': 'duplicate_borrow'
            }), 200

        # Tạo phiếu mượn mới
        borrow = Borrow(
            user_id=session['user_id'], 
            book_id=book.id, 
            book_title=book.title,
            borrow_date=datetime.now()
        )
        book.available_quantity -= 1
        
        db.session.add(borrow)
        db.session.flush()  # Để lấy được borrow.id

        # Thêm audit log
        audit = Audit(
            action='borrow',
            actor_user_id=session['user_id'],
            target_book_id=book.id,
            target_borrow_id=borrow.id,
            details=f'Người dùng {session["user_id"]} mượn sách {book.title}'
        )
        db.session.add(audit)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Mượn sách "{book.title}" thành công!',
            'new_quantity': book.available_quantity,
            'book_title': book.title
        })

    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi mượn sách: {str(e)}")  # Log lỗi để debug
        return jsonify({
            'success': False, 
            'message': 'Có lỗi xảy ra khi xử lý yêu cầu. Vui lòng thử lại sau.',
            'new_quantity': book.available_quantity if 'book' in locals() else None
        }), 500


@book.route('/return/cancel/<int:borrow_id>', methods=['POST'])
def cancel_return_request(borrow_id):
    """Allow user to cancel a previously sent return request."""
    if not session.get('user_id'):
        flash('Vui lòng đăng nhập để hủy yêu cầu trả sách.', 'warning')
        return redirect(url_for('auth_bp.login'))

    borrow = Borrow.query.get_or_404(borrow_id)
    if borrow.user_id != session['user_id']:
        flash('Bạn không có quyền hủy yêu cầu này.', 'danger')
        return redirect(url_for('user_bp.borrows'))

    if not borrow.return_requested:
        flash('Không có yêu cầu trả sách để hủy.', 'info')
        return redirect(url_for('user_bp.borrows'))

    borrow.return_requested = False
    borrow.return_requested_at = None
    try:
        audit = Audit(
            action='cancel_return_request',
            actor_user_id=session.get('user_id'),
            target_borrow_id=borrow.id,
            target_book_id=borrow.book_id,
            details=f'Người dùng {session.get("user_id")} hủy yêu cầu trả sách (borrow id {borrow.id})'
        )
        db.session.add(audit)
        db.session.commit()
        flash('Đã hủy yêu cầu trả sách.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi hủy yêu cầu trả sách: {str(e)}")
        flash('Có lỗi xảy ra khi hủy yêu cầu. Vui lòng thử lại!', 'danger')

    return redirect(url_for('user_bp.borrows'))

@book.route('/return/<int:borrow_id>', methods=['POST'])
def return_book(borrow_id):
    if not session.get('user_id'):
        flash('Vui lòng đăng nhập để trả sách.', 'warning')
        return redirect(url_for('auth_bp.login'))

    borrow = Borrow.query.get_or_404(borrow_id)
    if borrow.user_id != session['user_id'] and not session.get('is_admin'):
        flash('Bạn không có quyền trả sách này.', 'danger')
        return redirect(url_for('user_bp.borrows'))

    if borrow.return_date:
        flash('Sách đã được trả trước đó.', 'info')
        return redirect(url_for('user_bp.borrows'))
    # Admins may still mark the book as returned immediately (physical confirmation)
    if session.get('is_admin'):
        # perform immediate return (existing behavior)
        borrow.return_date = datetime.now()
        book = Book.query.get(borrow.book_id)
        if book:
            book.available_quantity = (book.available_quantity or 0) + 1
            # Thêm audit log
            try:
                audit = Audit(
                    action='return',
                    actor_user_id=session.get('user_id'),
                    target_borrow_id=borrow.id,
                    target_book_id=borrow.book_id,
                    details=f'Admin {session.get("user_id")} đánh dấu trả sách {book.title} (ID borrow {borrow.id})'
                )
                db.session.add(audit)
            except Exception as e:
                print(f"Lỗi khi tạo audit log: {str(e)}")

        try:
            db.session.commit()
            flash('Đã ghi nhận trả sách thành công!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi trả sách: {str(e)}")
            flash('Có lỗi xảy ra khi đánh dấu trả sách. Vui lòng thử lại!', 'danger')
        return redirect(url_for('admin_bp.user_history', user_id=borrow.user_id))

    # For normal users: create a return request instead of immediate return
    borrow.return_requested = True
    borrow.return_requested_at = datetime.now()
    try:
        # audit log for request
        audit = Audit(
            action='request_return',
            actor_user_id=session.get('user_id'),
            target_borrow_id=borrow.id,
            target_book_id=borrow.book_id,
            details=f'Người dùng {session.get("user_id")} yêu cầu trả sách (borrow id {borrow.id})'
        )
        db.session.add(audit)
        db.session.commit()
        flash('Yêu cầu trả sách đã gửi. Vui lòng đưa sách tới thủ thư để xác nhận.', 'info')
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi gửi yêu cầu trả sách: {str(e)}")
        flash('Có lỗi xảy ra khi gửi yêu cầu trả sách. Vui lòng thử lại!', 'danger')

    return redirect(url_for('user_bp.borrows'))