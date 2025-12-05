"""routes/main.py

Blueprint chính phục vụ trang người dùng (public):
 - index: trang chủ hiển thị sách phổ biến và sách mới
 - books: danh sách sách chung, hỗ trợ tìm kiếm và phân trang
 - category: lọc theo thể loại (slug -> display name thông qua CATEGORY_MAP)

Gợi ý: search hiện dùng SQLAlchemy `.like()`. Nếu cần tổ chức điều kiện phức tạp hơn, dùng `from sqlalchemy import or_`.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Book
from config import CATEGORY_MAP
from flask import jsonify, url_for
from sqlalchemy import or_


main = Blueprint('main', __name__)

# Route debug session cho kiểm tra OAuth
@main.route('/whoami')
def whoami():
    from flask import session, jsonify
    return jsonify(dict(session))


@main.route("/")
def index():
    """Trang chủ.

    - popular: lấy sách theo `quantity` giảm dần (giả sử quantity phản ánh mức phổ biến)
    - latest: lấy các sách mới thêm (sắp xếp theo id giảm dần)
    """
    popular = Book.query.filter_by(is_active=True).order_by(Book.quantity.desc(), Book.id.desc()).limit(9).all()
    latest = Book.query.filter_by(is_active=True).order_by(Book.id.desc()).limit(9).all()
    return render_template("user/home.html", popular=popular, latest=latest)


@main.route("/books")
def books():
    """Danh sách sách với search & pagination.

    Query params:
    - search: chuỗi tìm kiếm (title hoặc author)
    - page: trang phân trang
    """
    search = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)
    query = Book.query.filter_by(is_active=True)
    if search:
        # Lọc theo title hoặc author chứa chuỗi tìm kiếm
        query = query.filter(Book.title.like(f"%{search}%") | Book.author.like(f"%{search}%"))
    paginated = query.order_by(Book.id.desc()).paginate(page=page, per_page=9)
    return render_template("user/books.html", books=paginated, category=None, category_slug=None)


@main.route('/category/<slug>')
def category(slug):
    """Trang hiển thị sách theo thể loại slug.

    - Lấy display name từ CATEGORY_MAP; nếu không tồn tại, redirect về trang books.
    - Hỗ trợ tìm kiếm giống `books()`.
    """
    display = CATEGORY_MAP.get(slug)
    if not display:
        flash('Thể loại không tồn tại.', 'warning')
        return redirect(url_for('main_bp.books'))
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Book.query.filter_by(is_active=True, category=display)
    if search:
        query = query.filter(Book.title.like(f"%{search}%") | Book.author.like(f"%{search}%"))
    paginated = query.order_by(Book.id.desc()).paginate(page=page, per_page=9)
    return render_template('user/books.html', books=paginated, category=display, category_slug=slug)


@main.route('/_suggest_books')
def suggest_books():
    """Return JSON suggestions for search autocomplete.

    Query param: q
    Returns list of objects: {id, title, author, available_quantity, url}
    """
    q = (request.args.get('q') or '').strip()
    results = []
    if not q:
        return jsonify(results)

    # Simple tokenized OR search across title and author
    tokens = [t for t in q.split() if len(t) > 1]
    query = Book.query.filter(Book.is_active == True)
    if tokens:
        # build OR filters
        ors = []
        for t in tokens:
            pattern = f"%{t}%"
            ors.append(Book.title.ilike(pattern))
            ors.append(Book.author.ilike(pattern))
        query = query.filter(or_(*ors))
    else:
        query = query.filter((Book.title.ilike(f"%{q}%")) | (Book.author.ilike(f"%{q}%")))

    books = query.order_by(Book.id.desc()).limit(8).all()
    for b in books:
        results.append({
            'id': b.id,
            'title': b.title,
            'author': b.author,
            'available_quantity': getattr(b, 'available_quantity', 0) or 0,
            'url': url_for('book_bp.detail', book_id=b.id)
        })
    return jsonify(results)