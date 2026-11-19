from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Notification, User

notifications_bp = Blueprint(
    "notifications", __name__, url_prefix="/api/notifications"
)


def notify(user_id, ticket_id, text):
    """Adds a notification. The caller must commit the session."""
    db.session.add(Notification(user_id=user_id, ticket_id=ticket_id, text=text[:255]))


def notify_admins(ticket_id, text, exclude_user_id=None):
    """Notifies every admin (except one, if given). The caller must commit."""
    for admin in User.query.filter_by(role="admin").all():
        if admin.id != exclude_user_id:
            notify(admin.id, ticket_id, text)


def notification_to_dict(n):
    return {
        "id": n.id,
        "ticket_id": n.ticket_id,
        "text": n.text,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    user_id = int(get_jwt_identity())

    items = (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(20)
        .all()
    )
    unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()

    return jsonify({"unread": unread, "items": [notification_to_dict(n) for n in items]})


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@jwt_required()
def mark_read(notification_id):
    user_id = int(get_jwt_identity())

    n = db.session.get(Notification, notification_id)
    if not n or n.user_id != user_id:
        return jsonify({"error": "Notification not found"}), 404

    n.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"})


@notifications_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())

    Notification.query.filter_by(user_id=user_id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return jsonify({"message": "All marked as read"})