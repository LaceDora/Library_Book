"""routes/notification.py

Chứa các route xử lý thông báo:
- get_notifications: lấy danh sách thông báo (JSON)
- mark_read: đánh dấu đã đọc một thông báo
- mark_all_read: đánh dấu đã đọc tất cả
"""

from flask import Blueprint, jsonify, session, request
from models import db, Notification

notification_bp = Blueprint('notification_bp', __name__)

@notification_bp.route('/notifications', methods=['GET'])
def get_notifications():
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    # Lấy 10 thông báo gần nhất
    notifications = Notification.query.filter_by(user_id=session['user_id'])\
        .order_by(Notification.created_at.desc())\
        .limit(10).all()
    
    # Đếm số thông báo chưa đọc
    unread_count = Notification.query.filter_by(
        user_id=session['user_id'], 
        is_read=False
    ).count()

    return jsonify({
        'success': True,
        'unread_count': unread_count,
        'notifications': [{
            'id': n.id,
            'message': n.message,
            'link': n.link,
            'is_read': n.is_read,
            'type': n.type,
            'created_at': n.created_at.strftime('%d/%m/%Y %H:%M')
        } for n in notifications]
    })

@notification_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
def mark_read(notification_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@notification_bp.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_read():
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    Notification.query.filter_by(user_id=session['user_id'], is_read=False)\
        .update({Notification.is_read: True})
    
    db.session.commit()
    
    return jsonify({'success': True})
