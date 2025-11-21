/* static/js/main.js

Mục đích:
 - Xử lý các hành động phía client, hiện tại có: mượn sách qua AJAX (endpoint /book/borrow_ajax/<id>)
 - Hiển thị toast notification tùy loại (success/warning/error)

Ghi chú:
 - Kiểm tra meta[name="user-logged-in"] để biết user đã đăng nhập hay chưa.
 - Đảm bảo server chấp nhận header 'X-Requested-With': 'XMLHttpRequest'.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Xử lý mượn sách qua AJAX
    document.querySelectorAll('.borrow-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Kiểm tra đăng nhập
            if (!document.querySelector('meta[name="user-logged-in"]')) {
                showToast('error', 'Thông báo', 'Vui lòng đăng nhập để mượn sách.');
                window.location.href = '/auth/login';
                return;
            }

            const bookId = this.dataset.bookId;
            
            // Disable nút ngay khi click để tránh double-submit
            button.disabled = true;
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

            fetch(`/book/borrow_ajax/${bookId}`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Cập nhật số lượng sách
                const qtyElement = document.getElementById(`book-qty-${bookId}`);
                if (qtyElement && typeof data.new_quantity !== 'undefined') {
                    qtyElement.textContent = data.new_quantity;
                }

                // Cập nhật trạng thái nút dựa vào số lượng
                if (data.new_quantity <= 0) {
                    button.classList.remove('btn-success');
                    button.classList.add('btn-secondary');
                    button.disabled = true;
                    button.innerHTML = 'Hết';
                } else {
                    button.classList.remove('btn-secondary');
                    button.classList.add('btn-success');
                    button.disabled = false;
                    button.innerHTML = originalText;
                }

                // Xử lý thông báo dựa trên phản hồi từ server
                if (data.success) {
                    showToast('success', 'Thành công', data.message);
                } else if (data.error_type === 'duplicate_borrow') {
                    showToast('warning', 'Thông báo', data.message);
                } else {
                    showToast('error', 'Thông báo', data.message);
                }
            })
            .catch(error => {
                console.error('Lỗi:', error);
                button.disabled = false;
                button.innerHTML = originalText;
                showToast('error', 'Lỗi', 'Lỗi kết nối, vui lòng thử lại sau.');
            });
        });
    });

    // Hàm hiển thị toast message
    function showToast(type, title, message) {
        // Xác định màu của toast dựa trên loại
        let bgClass;
        switch(type) {
            case 'success':
                bgClass = 'bg-success'
                break;
            case 'warning':
                bgClass = 'bg-warning text-dark';
                break;
            case 'error':
                bgClass = 'bg-danger';
                break;
            default:
                bgClass = 'bg-primary';
        }

        // Create and show the toast using Bootstrap
        const container = document.getElementById('ajaxToastContainer');
        if (!container) return;
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : (type === 'success' ? 'success' : 'primary')} border-0`;
        toast.role = 'alert';
        toast.ariaLive = 'assertive';
        toast.ariaAtomic = 'true';
        toast.id = toastId;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>`;
        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        // remove from DOM when hidden
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    // Password toggle handler for any .toggle-btn
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', function(){
            const targetId = this.getAttribute('aria-controls');
            if(!targetId) return;
            const input = document.getElementById(targetId);
            if(!input) return;
            const wasHidden = input.type === 'password';
            const labelEl = this.querySelector('.toggle-label');
            const icon = this.querySelector('i.bi');
            if(wasHidden) {
                input.type = 'text';
                if(labelEl) labelEl.textContent = 'Ẩn';
                this.setAttribute('aria-pressed', 'true');
                this.setAttribute('aria-label', 'Ẩn mật khẩu');
                if(icon){ icon.classList.remove('bi-eye'); icon.classList.add('bi-eye-slash'); }
            } else {
                input.type = 'password';
                if(labelEl) labelEl.textContent = 'Hiện';
                this.setAttribute('aria-pressed', 'false');
                this.setAttribute('aria-label', 'Hiện mật khẩu');
                if(icon){ icon.classList.remove('bi-eye-slash'); icon.classList.add('bi-eye'); }
            }
        });
    });
});