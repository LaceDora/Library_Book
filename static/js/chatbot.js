let isOpen = false;
const CHAT_HISTORY_KEY = 'chatbot_history';
const MAX_HISTORY_ITEMS = 100;

document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo chatbot UI khi trang tải xong
    initializeChatbot();

    // Xử lý sự kiện click vào nút chatbot
    document.querySelector('.chatbot-button').addEventListener('click', toggleChatbox);
    
    // Xử lý sự kiện gửi tin nhắn
    document.querySelector('.chatbot-input-form').addEventListener('submit', handleSubmit);
    
    // Tải lịch sử chat từ localStorage
    loadChatHistory();
});

function initializeChatbot() {
    const chatbotHTML = `
        <div class="chatbot-container">
            <button class="chatbot-button">
                <i class="bi bi-chat-dots-fill"></i>
            </button>
            
            <div class="chatbot-box">
                <div class="chatbot-header">
                    <div class="chatbot-title">
                        <i class="bi bi-robot"></i>
                        <span>Library Assistant</span>
                    </div>
                    <div class="chatbot-header-actions">
                        <button class="chatbot-clear-history" title="Xóa lịch sử">
                            <i class="bi bi-trash"></i>
                        </button>
                        <button class="chatbot-close">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>
                
                <div class="chatbot-messages">
                    <div class="message bot-message">
                        Xin chào! Tôi có thể giúp gì cho bạn?
                    </div>
                </div>
                
                <form class="chatbot-input-form">
                    <input type="text" placeholder="Nhập tin nhắn..." required>
                    <button type="submit">
                        <i class="bi bi-send-fill"></i>
                    </button>
                </form>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', chatbotHTML);
    
    // Thêm event listener cho nút đóng
    document.querySelector('.chatbot-close').addEventListener('click', toggleChatbox);
    
    // Thêm event listener cho nút xóa lịch sử
    document.querySelector('.chatbot-clear-history').addEventListener('click', clearChatHistory);
}

function toggleChatbox() {
    const chatbox = document.querySelector('.chatbot-box');
    const button = document.querySelector('.chatbot-button');
    
    isOpen = !isOpen;
    chatbox.style.display = isOpen ? 'flex' : 'none';
    button.classList.toggle('active');
    
    if (isOpen) {
        document.querySelector('.chatbot-input-form input').focus();
    }
}

function saveChatHistory() {
    // Lưu lịch sử chat vào localStorage
    const messagesDiv = document.querySelector('.chatbot-messages');
    const messages = [];
    
    messagesDiv.querySelectorAll('.message').forEach(msg => {
        // Bỏ qua loading messages
        if (!msg.classList.contains('loading')) {
            const sender = msg.classList.contains('bot-message') ? 'bot' : 'user';
            messages.push({
                sender: sender,
                text: msg.textContent,
                timestamp: Date.now()
            });
        }
    });
    
    // Giới hạn lịch sử đến MAX_HISTORY_ITEMS
    if (messages.length > MAX_HISTORY_ITEMS) {
        messages.splice(0, messages.length - MAX_HISTORY_ITEMS);
    }
    
    try {
        localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(messages));
    } catch (e) {
        console.warn('Không thể lưu lịch sử chat:', e);
    }
}

function loadChatHistory() {
    // Tải lịch sử chat từ localStorage
    try {
        const saved = localStorage.getItem(CHAT_HISTORY_KEY);
        if (!saved) return;
        
        const messages = JSON.parse(saved);
        const messagesDiv = document.querySelector('.chatbot-messages');
        
        // Xóa tin nhắn mặc định nếu có lịch sử
        if (messages.length > 0) {
            messagesDiv.innerHTML = '';
        }
        
        // Tải lại các tin nhắn
        messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.sender}-message`;
            messageDiv.textContent = msg.text;
            messagesDiv.appendChild(messageDiv);
        });
        
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (e) {
        console.warn('Không thể tải lịch sử chat:', e);
    }
}

function clearChatHistory() {
    // Xóa lịch sử chat
    if (confirm('Bạn có chắc muốn xóa toàn bộ lịch sử chat?')) {
        localStorage.removeItem(CHAT_HISTORY_KEY);
        const messagesDiv = document.querySelector('.chatbot-messages');
        messagesDiv.innerHTML = `<div class="message bot-message">Xin chào! Tôi có thể giúp gì cho bạn?</div>`;
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    
    const input = e.target.querySelector('input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Hiển thị tin nhắn của người dùng
    appendMessage('user', message);
    input.value = '';
    
    // Hiển thị loading
    const loadingId = showLoading();
    
    try {
        const response = await fetchGPTResponse(message);
        // Xóa loading và hiển thị câu trả lời
        removeLoading(loadingId);
        appendMessage('bot', response);
    } catch (error) {
        removeLoading(loadingId);
        appendMessage('bot', 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.');
        console.error('Error:', error);
    }
}

function appendMessage(sender, message) {
    const messagesDiv = document.querySelector('.chatbot-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = message;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Tự động lưu lịch sử sau mỗi tin nhắn
    saveChatHistory();
}

function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-message loading';
    loadingDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    document.querySelector('.chatbot-messages').appendChild(loadingDiv);
    return Date.now(); // Dùng timestamp làm id
}

function removeLoading(loadingId) {
    const loadingDiv = document.querySelector('.loading');
    if (loadingDiv) loadingDiv.remove();
}

async function fetchGPTResponse(message) {
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || 'Server request failed');
    }

    const data = await response.json();
    if (data.reply) return data.reply;
    throw new Error('Invalid response from server');
}