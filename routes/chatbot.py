from flask import Blueprint, request, jsonify
import requests
from dotenv import load_dotenv
import os
import time
import difflib
import unicodedata
import re
import string

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds, will be doubled each retry

# Gemini API endpoints
BASE_API_URL = "https://generativelanguage.googleapis.com/v1"
MODELS_URL = f"{BASE_API_URL}/models"
GEMINI_MODEL = "gemini-2.0-flash-lite"  # Using the faster, lighter Flash model
GEMINI_API_URL = f"{BASE_API_URL}/models/{GEMINI_MODEL}:generateContent"

def list_available_models():
    """List available models from the API"""
    try:
        response = requests.get(f"{MODELS_URL}?key={GOOGLE_API_KEY}")
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model["name"] for model in models]
        return []
    except Exception as e:
        print(f"Error listing models: {str(e)}")
        return []

def get_website_context(query):
    """Get relevant context from the database based on the query"""
    from models import Book, Borrow, User, db
    context_lines = []

    try:
        # Làm mới tất cả dữ liệu từ database để lấy số liệu mới nhất
        db.session.expire_all()
        
        q = f"%{query}%"
        print(f"\n=== Starting get_website_context for query: {query} ===")

        # Kiểm tra xem user hỏi về một hoặc nhiều thể loại cụ thể
        category_map = {
            'lập trình': 'Lập trình',
            'programming': 'Lập trình',
            'âm nhạc': 'Âm nhạc',
            'truyện tranh': 'Truyện tranh',
            'y học': 'Y học',
            'tâm lý': 'Tâm lý'
        }
        
        # Kiểm tra xem user hỏi về TẤT CẢ thể loại hay các thể loại cụ thể
        is_asking_all_categories = any(word.lower() in query.lower() for word in ['tất cả', 'toàn bộ', 'mỗi', 'từng'])
        
        # Tìm tất cả thể loại trong query
        matched_categories = []
        for keyword, category in category_map.items():
            if keyword.lower() in query.lower() and category not in matched_categories:
                matched_categories.append(category)
        
        # Nếu user hỏi về TẤT CẢ hoặc không nêu thể loại cụ thể nhưng có yêu cầu liệt kê
        if is_asking_all_categories or (not matched_categories and any(word.lower() in query.lower() for word in ['tất cả', 'toàn bộ', 'mỗi', 'từng', 'các'])):
            matched_categories = list(set(category_map.values()))  # Lấy tất cả các thể loại duy nhất
            print(f"User requesting all categories: {matched_categories}")
        
        # Nếu user hỏi về một hoặc nhiều thể loại (CỤ THỂ hoặc TẤT CẢ), lấy danh sách chi tiết sách
        if matched_categories and any(word.lower() in query.lower() for word in ['tên', 'liệt kê', 'danh sách', 'những', 'cuốn', 'kể', 'còn', 'hết']):
            print(f"User requesting detailed list for categories: {matched_categories}")

            # Kiểm tra xem câu truy vấn có vẻ đề cập tới một tựa sách cụ thể hay không.
            # Nếu có, ta sẽ để phần tìm sách cụ thể xử lý trước (không liệt kê toàn bộ thể loại).
            has_specific_book_keywords = any(word.lower() in query.lower() for word in ['python', 'fluent', 'clean', 'code', 'flask', 'javascript', 'guitar', 'piano', 'âm', 'âm nhạc', 'tâm lý', 'y học', 'mạng', 'giải thuật'])

            if has_specific_book_keywords:
                print("Query looks like specific book search, skipping category list for now")
            else:
                # Người dùng thực sự muốn liệt kê theo thể loại
                try:
                    want_available_only = any(word.lower() in query.lower() for word in ['còn', 'còn sẵn', 'còn mấy', 'sẵn'])
                    want_unavailable_only = any(word.lower() in query.lower() for word in ['hết', 'hết sách', 'không còn'])

                    query_obj = db.session.query(Book).filter(Book.category.in_(matched_categories)).filter(Book.is_active == True)

                    if want_available_only:
                        query_obj = query_obj.filter(Book.available_quantity > 0)
                        print("Filtering for available books only")
                    elif want_unavailable_only:
                        query_obj = query_obj.filter(Book.available_quantity == 0)
                        print("Filtering for unavailable books only")

                    books = query_obj.all()
                    print(f"✓ Found {len(books)} books in categories {matched_categories}")

                except Exception as e:
                    print(f"✗ Detailed category query failed: {e}")
                    books = []

                if books:
                    total_available = sum(getattr(b, 'available_quantity', 0) or 0 for b in books)

                    # Header thông tin chung
                    if len(matched_categories) == 1:
                        context_lines.append(f"📚 DANH SÁCH SÁCH - Thể loại: {matched_categories[0]}")
                        context_lines.append(f"{'='*70}")
                        context_lines.append(f"Tổng: {len(books)} cuốn sách | {total_available} quyển có sẵn")
                    else:
                        context_lines.append(f"📚 DANH SÁCH SÁCH - {len(matched_categories)} Thể Loại")
                        context_lines.append(f"{'='*70}")
                        context_lines.append(f"Tổng: {len(books)} cuốn sách | {total_available} quyển có sẵn")

                    context_lines.append("")

                    # Sắp xếp sách theo thể loại để hiển thị dễ nhìn hơn
                    books_by_category = {}
                    for b in books:
                        cat = getattr(b, 'category', 'Khác')
                        books_by_category.setdefault(cat, []).append(b)

                    for category in matched_categories:
                        if category in books_by_category:
                            book_list = books_by_category[category]
                            context_lines.append(f"📖 {category.upper()}")
                            context_lines.append(f"{'-'*70}")
                            for idx, b in enumerate(book_list, 1):
                                available_qty = getattr(b, 'available_quantity', 0) or 0
                                availability_status = "✅ Còn sẵn" if available_qty > 0 else "❌ Hết sách"
                                context_lines.append(f"{idx}. {b.title}")
                                context_lines.append(f"   Tác giả: {b.author}")
                                context_lines.append(f"   Số lượng: {available_qty} quyển | {availability_status}")
                                context_lines.append("")

                    # Footer thống kê
                    context_lines.append(f"{'='*70}")
                    context_lines.append(f"📊 TÓM LẠI: {len(books)} cuốn sách khác nhau | {total_available} quyển có sẵn")
                    print(f"✓ Context successfully built with {len(context_lines)} lines")
                    print("=== End get_website_context ===\n")
                    return "\n".join(context_lines)
        
        # Nếu chỉ detect thể loại nhưng không có từ khóa yêu cầu danh sách, thì skip
        if matched_categories:
            print(f"Detected category {matched_categories} but no list request keywords found")
        
        # TRƯỚC TIÊN: Thử tìm kiếm sách theo tên/tác giả (có thể kèm từ khóa như "còn mấy")
        print("Attempting to search for specific book by title/author...")

        # 1) Nếu user đưa tiêu đề trong ngoặc kép: lấy đó làm tiêu đề chính xác
        quoted = re.search(r'"([^\"]+)"|\'([^\']+)\'', query)
        if quoted:
            # lấy nội dung trong ngoặc kép
            search_query = quoted.group(1) or quoted.group(2)
            search_keywords = [search_query]
            print(f"Using quoted search query: {search_query}")
        else:
            # 2) Loại bỏ dấu câu
            query_cleaned = query.translate(str.maketrans('', '', string.punctuation))
            # 3) Chuẩn hóa unicode (NFKC) nhưng giữ dấu tiếng Việt
            query_cleaned = unicodedata.normalize('NFKC', query_cleaned)

            # 4) Lọc từ: loại bỏ trợ từ/đại từ/động từ chung, giữ danh từ quan trọng
            filler_words = {
                'sách', 'cuốn', 'tác', 'giả', 'về', 'bao', 'nhiêu', 'được', 'hay', 'là', 'cái', 
                'thư', 'viện', 'ở', 'của', 'tôi', 'bạn', 'cô', 'ông', 'bà', 'anh', 'em', 'chị', 'em',
                'là', 'cái', 'này', 'nọ', 'kia', 'đó', 'nên', 'và', 'hoặc', 'nhưng', 'mà',
                'đang', 'đã', 'sẽ', 'có', 'không', 'chưa', 'còn', 'được', 'mấy', 'rồi'
            }
            tokens = [w for w in query_cleaned.lower().split() if w not in filler_words and len(w) > 1]
            search_keywords = tokens if tokens else []
            search_query = ' '.join(tokens)
            
            print(f"Search keywords extracted: {search_keywords} | Full query: {search_query}")

        # Xác định intent về số lượng (nếu user hỏi "còn mấy", "còn bao nhiêu", hoặc đã nêu số cụ thể)
        want_count = bool(re.search(r'\b(mấy|bao nhiêu|còn\s+mấy|còn|còn\s+bao nhiêu)\b', query.lower()))
        explicit_number = None
        mnum = re.search(r'còn\s*(\d+)\b', query.lower())
        if mnum:
            explicit_number = int(mnum.group(1))

        # Tìm kiếm: trước tiên cố tìm toàn bộ chuỗi, sau đó từng từ khóa riêng lẻ
        books = []
        
        if search_query and len(search_query) > 1:
            try:
                # Thử 1: Tìm toàn bộ chuỗi
                search_pattern = f"%{search_query}%"
                books = (
                    db.session.query(Book)
                    .filter((Book.title.ilike(search_pattern)) | (Book.author.ilike(search_pattern)))
                    .filter(Book.is_active == True)
                    .limit(10)
                    .all()
                )
                print(f"Full query search returned {len(books)} book(s)")
            except Exception as e:
                print(f"✗ Full query search failed: {e}")
        
        # Thử 2: Nếu toàn bộ không được, tìm bằng HOẶC các từ khóa riêng lẻ (ANY match)
        if not books and search_keywords:
            try:
                or_filters = []
                for keyword in search_keywords:
                    pattern = f"%{keyword}%"
                    or_filters.append(Book.title.ilike(pattern))
                    or_filters.append(Book.author.ilike(pattern))
                
                if or_filters:
                    from sqlalchemy import or_
                    books = (
                        db.session.query(Book)
                        .filter(or_(*or_filters))
                        .filter(Book.is_active == True)
                        .limit(10)
                        .all()
                    )
                    print(f"OR search (individual keywords) returned {len(books)} book(s)")
            except Exception as e:
                print(f"✗ OR search failed: {e}")
        
        if books:
            print(f"✓ Found {len(books)} book(s) by search")
            context_lines.append("📚 Sách bạn tìm:")
            for idx, b in enumerate(books, 1):
                available_qty = getattr(b, 'available_quantity', 0) or 0
                availability_status = "✅ Còn sẵn" if available_qty > 0 else "❌ Hết sách"
                context_lines.append(f"{idx}. {b.title}")
                context_lines.append(f"   Tác giả: {b.author}")
                context_lines.append(f"   Thể loại: {b.category}")
                context_lines.append(f"   Số lượng: {available_qty} quyển | {availability_status}")
                context_lines.append("")
            print(f"✓ Context built with book details")
            print("=== End get_website_context ===\n")
            return "\n".join(context_lines)
        else:
            print(f"✗ No books found with search query")

        # Nếu không tìm thấy chính xác, thử fuzzy match trên danh sách tiêu đề
        try:
            print("Trying fuzzy match fallback for titles...")
            titles = [t[0] if isinstance(t, tuple) else getattr(t, 'title', '') for t in db.session.query(Book.title).filter(Book.is_active == True).all()]
            # Thử fuzzy match với từng keyword
            candidates = set()
            for keyword in search_keywords:
                matches = difflib.get_close_matches(keyword, titles, n=3, cutoff=0.5)
                candidates.update(matches)
            
            candidates = list(candidates)
            print(f"Fuzzy candidates: {candidates}")
            if candidates:
                books = (
                    db.session.query(Book)
                    .filter(Book.title.in_(candidates))
                    .filter(Book.is_active == True)
                    .all()
                )
                if books:
                    context_lines.append("📚 Có thể bạn muốn nói đến:")
                    for idx, b in enumerate(books, 1):
                        available_qty = getattr(b, 'available_quantity', 0) or 0
                        availability_status = "✅ Còn sẵn" if available_qty > 0 else "❌ Hết sách"
                        context_lines.append(f"{idx}. {b.title} — {b.author} | {available_qty} quyển {availability_status}")
                    context_lines.append("")
                    context_lines.append("(Gợi ý các tựa gần khớp với truy vấn của bạn)")
                    print("✓ Returned fuzzy match suggestions")
                    return "\n".join(context_lines)
        except Exception as ef:
            print(f"✗ Fuzzy matching failed: {ef}")
        
        # Nếu không tìm được sách cụ thể, kiểm tra xem user hỏi về một thể loại cụ thể hay tổng thống kê
        specific_category = None
        for keyword, category in category_map.items():
            if keyword.lower() in query.lower():
                specific_category = category
                print(f"Detected specific category: {specific_category}")
                break
        
        # Nếu hỏi về thống kê tổng quát (không phải thể loại cụ thể)
        stat_keywords = {'thể loại', 'bao nhiêu', 'tổng', 'thống kê', 'mấy', 'có'}
        is_asking_for_stats = any(keyword.lower() in query.lower() for keyword in stat_keywords)
        
        if is_asking_for_stats and not specific_category:
            print("User asking about general statistics/categories...")
            try:
                # Get all categories with book count and total available_quantity
                categories_data = (
                    db.session.query(Book.category, db.func.count(Book.id).label('count'), db.func.sum(Book.available_quantity).label('total_available'))
                    .filter(Book.is_active == True)
                    .group_by(Book.category)
                    .all()
                )
                
                if categories_data:
                    context_lines.append("Thống kê thể loại sách trong thư viện:")
                    context_lines.append(f"Tổng số thể loại: {len(categories_data)}")
                    context_lines.append("")
                    
                    total_books = 0
                    total_available = 0
                    
                    for category, count, available_qty in categories_data:
                        available_qty = available_qty or 0
                        total_books += count
                        total_available += available_qty
                        context_lines.append(f"• {category}: {count} cuốn sách, {available_qty} quyển có sẵn")
                    
                    context_lines.append("")
                    context_lines.append(f"Tổng cộng: {total_books} cuốn sách khác nhau, {total_available} quyển có sẵn trong kho")
                    
                    print(f"✓ Found {len(categories_data)} categories")
                    print("=== End get_website_context ===\n")
                    return "\n".join(context_lines)
            except Exception as e:
                print(f"✗ Statistics query failed: {e}")

        # Original query - Try SQLAlchemy model query - search by title, author, category, and also full-text
        try:
            print("Attempting SQLAlchemy query on Book model...")
            books = (
                db.session.query(Book)
                .filter((Book.title.ilike(q)) | (Book.author.ilike(q)) | (Book.category.ilike(q)))
                .filter(Book.is_active == True)  # Only active books
                .limit(10)
                .all()
            )
            print(f"✓ SQLAlchemy book query returned {len(books)} rows")
            
            # Print details of each book found
            for idx, b in enumerate(books):
                print(f"  Book {idx+1}: {b.title} - Category: {b.category} - Qty: {getattr(b, 'quantity', 0)}")
        except Exception as e_inner:
            print(f"✗ SQLAlchemy query failed: {e_inner}")
            import traceback
            print(traceback.format_exc())
            books = []

        if books:
            context_lines.append("📚 Sách khả dụng trong thư viện:")
            for b in books:
                # Some deployments may not have a description column; handle defensively
                desc = getattr(b, 'description', '') or ''
                available_qty = getattr(b, 'available_quantity', 0) or 0
                availability_status = "✅ Còn sẵn" if available_qty > 0 else "❌ Hết sách"
                if desc:
                    context_lines.append(f"• {b.title} ({b.author}) - Thể loại: {getattr(b, 'category', '')} - Mô tả: {desc} - Số lượng: {available_qty} - {availability_status}")
                else:
                    context_lines.append(f"• {b.title} ({b.author}) - Thể loại: {getattr(b, 'category', '')} - Số lượng: {available_qty} - {availability_status}")
            return "\n".join(context_lines)

        # Nếu không tìm thấy kết quả từ search theo keyword, thử raw SQL fallback
        print("No exact match found, trying raw SQL fallback...")
        try:
            sql = f"SELECT title, author, category, available_quantity, description FROM book WHERE (title LIKE :q OR author LIKE :q OR category LIKE :q) AND is_active = 1 LIMIT 10"
            print(f"  Executing raw SQL...")
            res = db.session.execute(db.text(sql), {"q": q}).fetchall()
            print(f"✓ Raw SQL returned {len(res)} rows")
            
            if res:
                context_lines.append("📚 Sách khả dụng trong thư viện:")
                for idx, row in enumerate(res):
                    title = row[0]
                    author = row[1]
                    category = row[2] if len(row) > 2 else ''
                    available_qty = row[3] if len(row) > 3 else 0
                    desc = row[4] if len(row) > 4 else ''
                    availability_status = "✅ Còn sẵn" if available_qty and available_qty > 0 else "❌ Hết sách"
                    print(f"  Book {idx+1}: {title} - Available: {available_qty}")
                    if desc:
                        context_lines.append(f"• {title} ({author}) - Thể loại: {category} - Mô tả: {desc} - Số lượng: {available_qty} - {availability_status}")
                    else:
                        context_lines.append(f"• {title} ({author}) - Thể loại: {category} - Số lượng: {available_qty} - {availability_status}")
                return "\n".join(context_lines)
        except Exception as e_raw:
            print(f"✗ Raw SQL failed: {e_raw}")

        # If still empty, return empty string to indicate no context found
        if not context_lines:
            print("✗ No context found in DB for query:", query)
            print("=== End get_website_context (no results) ===\n")
            return ""

        print(f"✓ Context successfully built with {len(context_lines)} lines")
        print("=== End get_website_context ===\n")
        return "\n".join(context_lines)
    except Exception as e:
        print(f"✗ Error getting website context: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("=== End get_website_context (error) ===\n")
        return ""

        # 3) Search borrowing history (SQLAlchemy join). If it errors or returns nothing, try raw SQL as fallback
        borrows = []
        try:
            print("Attempting SQLAlchemy borrow query...")
            borrows = (
                db.session.query(Borrow, Book, User)
                .join(Book, Borrow.book_id == Book.id)
                .join(User, Borrow.user_id == User.id)
                .filter((Book.title.ilike(q)) | (User.username.ilike(q)))
                .limit(5)
                .all()
            )
            print(f"✓ SQLAlchemy borrow query returned {len(borrows)} rows")
        except Exception as e_join:
            print(f"✗ Borrow join query failed: {e_join}")
            borrows = []

        if borrows:
            context_lines.append("\n📖 Lịch sử mượn sách gần đây:")
            for br, bk, us in borrows:
                borrow_date = getattr(br, 'borrow_date', None)
                context_lines.append(f"• {bk.title} được mượn bởi {us.username} vào {borrow_date}")

        return "\n".join(context_lines) if context_lines else ""
    except Exception as e:
        print(f"✗ Error getting website context: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("=== End get_website_context (error) ===\n")
        return ""

def get_ai_response(prompt):
    """Get response from Gemini API via REST with retry logic"""
    # First, list available models for debugging
    models = list_available_models()
    print("Available models:", models)
    
    # Get relevant context from website
    context = get_website_context(prompt)
    
    # Check if our chosen Gemini model is available in the model list
    model_name = f"models/{GEMINI_MODEL}"
    if model_name not in models:
        print(f"{model_name} không có sẵn. Các mô hình có sẵn:", models)
        return "Xin lỗi, mô hình AI hiện không khả dụng. Vui lòng thử lại sau."
    
    retry_count = 0
    last_error = None
    
    while retry_count < MAX_RETRIES:
        try:
            print(f"Gọi Gemini API với prompt: {prompt} (Lần thử {retry_count + 1}/{MAX_RETRIES})")
            
            # Prepare the request
            headers = {
                "Content-Type": "application/json"
            }
            
            # Construct system prompt with context and instructions
            # Detect language and respond accordingly
            system_prompt = """Bạn là một trợ lý thư viện hữu ích. Trả lời các câu hỏi dựa trên thông tin thư viện được cung cấp.
LUÔN SỬ DỤNG THÔNG TIN VỀ TÍNH KHẢ DỤNG:
- Nếu sách có số lượng > 0 và trạng thái "Còn sẵn", hãy nói rằng sách ĐANG CÓ TRONG THƯ VIỆN
- Nếu sách có số lượng = 0 và trạng thái "Hết sách", hãy nói rằng sách KHÔNG CÓ HOẶC HẾT SÁCH
- Bao gồm số lượng còn lại trong trả lời khi hỏi về tính khả dụng

QUAN TRỌNG:
- Khi trả lời, GIỮ NGUYÊN toàn bộ thông tin từ bối cảnh (context) được cung cấp
- KHÔNG ĐƯỢC chỉnh sửa, thay đổi hay reformat nội dung từ context
- GIỮ NGUYÊN emoji, dấu chấm, định dạng ban đầu từ context
- Chỉ thêm giải thích nếu cần thiết

Nếu bối cảnh chứa thông tin liên quan, hãy sử dụng nó để cung cấp câu trả lời chính xác.
Nếu bạn không tìm thấy thông tin liên quan trong bối cảnh, hãy nói rõ là không tìm thấy.
Luôn lịch sự, chuyên nghiệp và trả lời bằng TIẾNG VIỆT."""
            
            if context:
                system_prompt += f"\n\nThông tin thư viện hiện có:\n{context}"
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": f"{system_prompt}\n\nCâu hỏi của người dùng: {prompt}\n\nTrợ lý:"
                    }]
                }]
            }
            
            # Add API key as query parameter
            url = f"{GEMINI_API_URL}?key={GOOGLE_API_KEY}"
            
            # Make the request
            print(f"Making request to: {url}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"Gemini API Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            # Handle non-200 responses
            if response.status_code != 200:
                error_text = response.text
                print(f"Gemini API Error Response: {error_text}")
                
                # Try to extract error message from JSON response
                try:
                    error_json = response.json()
                    error_message = error_json.get("error", {}).get("message", "Unknown error")
                    error_code = error_json.get("error", {}).get("code", 0)
                    print(f"Error details: {error_message} (Code: {error_code})")
                    
                    # Handle rate limiting (429) - Giới hạn retry chỉ 1 lần, chờ lâu hơn
                    if error_code == 429:
                        if retry_count == 0:  # Chỉ retry 1 lần (retry_count từ 0 → 1)
                            wait_time = 10  # Chờ 10 giây
                            print(f"Rate limited (429). Waiting {wait_time} seconds before single retry...")
                            time.sleep(wait_time)
                            retry_count += 1
                            continue
                        else:
                            # Đã retry rồi, vẫn lỗi 429 → báo rõ cho user
                            last_error = "Xin lỗi, API quá tải. Vui lòng thử lại sau vài phút."
                            return last_error
                    
                    # Các lỗi khác: không retry, trả lỗi luôn
                    last_error = f"Xin lỗi, có lỗi xảy ra: {error_message}"
                    return last_error
                except Exception as parse_error:
                    print(f"Failed to parse error JSON: {parse_error}")
                    last_error = "Xin lỗi, có lỗi khi liên lạc với mô hình AI."
                    return last_error
            else:
                # Parse response
                result = response.json()
                print(f"Gemini API Response: {result}")
                
                # Extract text from response
                if (result.get("candidates") and 
                    result["candidates"][0].get("content") and 
                    result["candidates"][0]["content"].get("parts")):
                    return result["candidates"][0]["content"]["parts"][0].get("text")
                
                print("No valid text in response")
                return "Xin lỗi, tôi không thể tạo phản hồi phù hợp."
            
        except requests.exceptions.Timeout:
            print(f"Request timeout on attempt {retry_count + 1}")
            last_error = "Xin lỗi, yêu cầu hết thời gian chờ. Vui lòng thử lại."
            if retry_count < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** retry_count)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                return last_error
        except Exception as e:
            print(f"Error calling Gemini API on attempt {retry_count + 1}: {str(e)}")
            last_error = f"Xin lỗi, có lỗi xảy ra: {str(e)}"
            if retry_count < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** retry_count)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                import traceback
                print(traceback.format_exc())
                return last_error
    
    # Max retries exhausted
    return last_error if last_error else "Xin lỗi, không thể lấy phản hồi sau nhiều lần thử."

chatbot = Blueprint('chatbot_bp', __name__)

@chatbot.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Không có tin nhắn nào được cung cấp'}), 400

    if not GOOGLE_API_KEY:
        return jsonify({'error': 'Không được cấu hình khóa API Google'}), 500

    try:
        # Get response from Gemini API
        reply = get_ai_response(message)
        
        if not reply:
            return jsonify({
                'error': 'Không có phản hồi từ mô hình AI'
            }), 502

        return jsonify({'reply': reply})
        
    except Exception as e:
        print(f'Chatbot error: {str(e)}')
        return jsonify({
            'error': 'Không thể lấy phản hồi từ mô hình AI',
            'detail': str(e)
        }), 502


@chatbot.route('/_debug_context', methods=['POST'])
def debug_context():
    """Debug endpoint to fetch website context for a query without calling the AI model.
    Use this to verify DB search logic and returned context quickly.
    """
    data = request.get_json() or {}
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        ctx = get_website_context(query)
        return jsonify({'query': query, 'context': ctx})
    except Exception as e:
        print(f'debug_context error: {e}')
        return jsonify({'error': 'failed to fetch context', 'detail': str(e)}), 500
