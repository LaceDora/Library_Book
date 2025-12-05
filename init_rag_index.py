from config import app
from models import db
from routes.chatbot import build_index

def init_index():
    print("Starting System Initialization...")
    with app.app_context():
        # 1. Create Tables
        print("Creating database tables...")
        db.create_all()
        print("✅ Tables created successfully.")

        # 2. Build RAG Index
        print("Starting RAG Indexing...")
        success, message = build_index()
        if success:
            print(f"✅ Indexing Success: {message}")
        else:
            print(f"❌ Indexing Error: {message}")

if __name__ == "__main__":
    init_index()
