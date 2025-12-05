from flask import Blueprint, request, jsonify
import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os
import logging
from models import Book, db

# Load environment variables
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint
chatbot = Blueprint('chatbot_bp', __name__)

# Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "library_books"
EMBEDDING_MODEL = "models/text-embedding-004"
CHAT_MODEL = "gemini-2.0-flash-lite"

# Initialize Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    logger.error("GOOGLE_API_KEY not found in environment variables")

# Initialize ChromaDB
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Custom Embedding Function using Gemini API
    class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
        def __call__(self, input: list[str]) -> list[list[float]]:
            try:
                # Gemini API expects 'content' for embed_content, handling batching if needed
                # But for simplicity, we loop or use batch method if available.
                # The SDK supports batch embedding via embed_content(..., content=list)
                result = genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=input,
                    task_type="retrieval_document" # or retrieval_query depending on usage
                )
                return result['embedding']
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                return [[] for _ in input] # Return empty on error to avoid crash

    # Use our custom embedding function
    embedding_func = GeminiEmbeddingFunction()
    
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_func
    )
    logger.info(f"ChromaDB collection '{COLLECTION_NAME}' loaded. Count: {collection.count()}")

except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}")
    collection = None


def build_index():
    """Re-index all books from MySQL to ChromaDB"""
    if not collection:
        return False, "ChromaDB not initialized"
    
    try:
        # Fetch all active books
        books = Book.query.filter_by(is_active=True).all()
        
        if not books:
            return True, "No books to index"

        ids = []
        documents = []
        metadatas = []

        for book in books:
            # Create a rich text representation for embedding
            # Include Title, Author, Category, and Description
            text_content = f"Tựa sách: {book.title}. Tác giả: {book.author}. Thể loại: {book.category}. Mô tả: {book.description or 'Không có mô tả'}."
            
            ids.append(str(book.id))
            documents.append(text_content)
            metadatas.append({
                "title": book.title,
                "author": book.author,
                "category": book.category or "",
                "available_quantity": book.available_quantity or 0,
                "id": book.id
            })

        # Add to ChromaDB (upsert overwrites existing IDs)
        # Process in batches to avoid API limits if necessary, but for small library it's fine
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        return True, f"Indexed {len(books)} books successfully"
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        return False, str(e)


def get_rag_context(query_text, n_results=5):
    """Retrieve relevant books using Hybrid Approach (SQL + Vector Search)"""
    
    # 1. Keyword/Category Detection for "List All" queries
    query_lower = query_text.lower()
    
    # Map keywords to DB categories
    category_map = {
        'lập trình': 'Lập trình',
        'công nghệ': 'Lập trình',
        'code': 'Lập trình',
        'âm nhạc': 'Âm nhạc',
        'nhạc': 'Âm nhạc',
        'truyện tranh': 'Truyện tranh',
        'manga': 'Truyện tranh',
        'y học': 'Y học',
        'sức khỏe': 'Y học',
        'tâm lý': 'Tâm lý'
    }
    
    # Check if user wants to list books by category
    target_category = None
    for key, val in category_map.items():
        if key in query_lower:
            target_category = val
            break
            
    is_list_request = any(w in query_lower for w in ['tất cả', 'danh sách', 'liệt kê', 'những cuốn', 'các cuốn'])
    
    # --- STRATEGY A: SQL Category Search (High Precision for Lists) ---
    if target_category and is_list_request:
        try:
            books = Book.query.filter(
                Book.category == target_category, 
                Book.is_active == True
            ).all()
            
            if books:
                context_parts = [f"📚 **Danh sách sách thuộc thể loại {target_category}:**"]
                for i, book in enumerate(books):
                    status = "✅ Còn sẵn" if (book.available_quantity or 0) > 0 else "❌ Hết sách"
                    context_parts.append(f"{i+1}. **{book.title}**")
                    context_parts.append(f"   - Tác giả: {book.author}")
                    context_parts.append(f"   - Số lượng: {book.available_quantity or 0} ({status})")
                    context_parts.append("---")
                return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"SQL Category search failed: {e}")
            # Fallback to Vector Search if SQL fails

    # --- STRATEGY B: Specific Title Match (High Precision for specific books) ---
    # Since the library is small, we can check if any book title appears in the query
    try:
        # Get all titles to check against query
        all_books = Book.query.filter_by(is_active=True).all()
        found_specific_books = []
        
        for book in all_books:
            # Check if title is in query (case insensitive)
            if book.title.lower() in query_lower:
                found_specific_books.append(book)
        
        if found_specific_books:
            context_parts = ["📚 **Thông tin chi tiết sách bạn hỏi:**"]
            for book in found_specific_books:
                status = "✅ Còn sẵn" if (book.available_quantity or 0) > 0 else "❌ Hết sách"
                context_parts.append(f"**{book.title}**")
                context_parts.append(f"- Tác giả: {book.author}")
                context_parts.append(f"- Thể loại: {book.category}")
                context_parts.append(f"- Số lượng: {book.available_quantity or 0} ({status})")
                context_parts.append(f"- Lượt xem: {book.views_count or 0}")
                context_parts.append(f"- Mô tả: {book.description or 'Không có mô tả'}")
                context_parts.append("---")
            
            # If we found specific books, we can return immediately or combine with RAG
            # Returning immediately is safer to avoid noise
            return "\n".join(context_parts)
            
    except Exception as e:
        logger.error(f"Specific Title Match failed: {e}")

    # --- STRATEGY C: Vector Search (Semantic Search) ---
    if not collection:
        return ""
    
    try:
        # Query ChromaDB
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        # Format results
        context_parts = ["📚 **Sách liên quan tìm thấy trong thư viện:**"]
        
        if not results['documents'] or not results['documents'][0]:
            return "Không tìm thấy sách nào liên quan trong cơ sở dữ liệu."

        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            book_id = meta['id']
            
            # Fetch real-time quantity and views from DB
            real_time_qty = 0
            real_time_views = 0
            try:
                book = Book.query.get(book_id)
                if book:
                    real_time_qty = book.available_quantity or 0
                    real_time_views = book.views_count or 0
            except Exception as e:
                logger.error(f"Error fetching real-time data for book {book_id}: {e}")
                real_time_qty = meta.get('available_quantity', 0)

            status = "✅ Còn sẵn" if real_time_qty > 0 else "❌ Hết sách"
            
            context_parts.append(f"{i+1}. **{meta['title']}**")
            context_parts.append(f"   - Tác giả: {meta['author']}")
            context_parts.append(f"   - Thể loại: {meta['category']}")
            context_parts.append(f"   - Tình trạng: {real_time_qty} quyển ({status})")
            context_parts.append(f"   - Lượt xem: {real_time_views}")
            context_parts.append(f"   - Nội dung: {doc}") 
            context_parts.append("---")
            
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        return ""


def get_ai_response(user_message):
    """Generate response using Gemini with RAG context"""
    try:
        # 1. Get Context via RAG
        context = get_rag_context(user_message)
        
        # 2. Construct System Prompt
        system_instruction = """Bạn là trợ lý ảo thông minh của thư viện. Nhiệm vụ của bạn là hỗ trợ người dùng tìm kiếm sách và giải đáp thắc mắc về thư viện.

HƯỚNG DẪN TRẢ LỜI:
1. Dựa CHỦ YẾU vào thông tin được cung cấp trong phần 'THÔNG TIN TỪ THƯ VIỆN' dưới đây.
2. Nếu sách có trạng thái 'Còn sẵn' (>0), hãy báo cho người dùng biết là có thể mượn.
3. Nếu sách 'Hết sách' (0), hãy thông báo hiện tại đã hết.
4. Khi cung cấp thông tin CHI TIẾT về một cuốn sách cụ thể, BẮT BUỘC phải đề cập:
   - Tên sách
   - Tác giả
   - Thể loại
   - Số lượng còn lại
   - **LƯỢT XEM** (views_count) - KHÔNG ĐƯỢC BỎ QUA thông tin này
5. Nếu không tìm thấy thông tin trong ngữ cảnh, hãy nói khéo là bạn không tìm thấy sách đó trong thư viện, nhưng có thể đề xuất các sách khác nếu có trong danh sách.
6. Trả lời ngắn gọn, súc tích, thân thiện, sử dụng tiếng Việt tự nhiên.
7. KHÔNG bịa đặt thông tin sách không có trong ngữ cảnh.

THÔNG TIN TỪ THƯ VIỆN:
"""
        
        # 3. Call Gemini API
        model = genai.GenerativeModel(
            model_name=CHAT_MODEL,
            system_instruction=system_instruction
        )
        
        # Combine context and user message
        full_prompt = f"{context}\n\nCâu hỏi của người dùng: {user_message}"
        
        response = model.generate_content(full_prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"AI Generation failed: {e}")
        return "Xin lỗi, hệ thống đang gặp sự cố khi xử lý yêu cầu của bạn."


# --- Routes ---

@chatbot.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
        
    response_text = get_ai_response(message)
    return jsonify({'reply': response_text})


@chatbot.route('/rag/index', methods=['POST'])
def trigger_indexing():
    """Manually trigger re-indexing of books"""
    success, msg = build_index()
    if success:
        return jsonify({'status': 'success', 'message': msg})
    else:
        return jsonify({'status': 'error', 'message': msg}), 500

@chatbot.route('/rag/status', methods=['GET'])
def rag_status():
    """Check collection status"""
    if collection:
        return jsonify({
            'status': 'active', 
            'count': collection.count(),
            'db_path': CHROMA_DB_PATH
        })
    return jsonify({'status': 'inactive', 'error': 'Collection not initialized'})
