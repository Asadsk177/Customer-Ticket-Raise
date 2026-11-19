from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from extensions import db
from models import Attachment, Message, Notification, Ticket, User
from notifications import notify_admins

tickets_bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

# Change these to match AAR Technologies' real services
CATEGORIES = ["Software Support", "Hardware", "Billing", "Account", "General"]
PRIORITIES = ["Low", "Medium", "High"]


def ticket_to_dict(ticket):
    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


@tickets_bp.route("/categories", methods=["GET"])
def get_categories():
    return jsonify({"categories": CATEGORIES, "priorities": PRIORITIES})


@tickets_bp.route("", methods=["POST"])
@jwt_required()
def create_ticket():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category") or "General"
    priority = data.get("priority") or "Medium"

    if not title or not description:
        return jsonify({"error": "title and description are required"}), 400
    if len(title) > 200:
        return jsonify({"error": "Title is too long (max 200 characters)"}), 400
    if category not in CATEGORIES:
        return jsonify({"error": f"category must be one of {CATEGORIES}"}), 400
    if priority not in PRIORITIES:
        return jsonify({"error": f"priority must be one of {PRIORITIES}"}), 400

    ticket = Ticket(
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        status="Open",
    )
    db.session.add(ticket)
    db.session.flush()  # gives the ticket its id before we commit

    customer = db.session.get(User, user_id)
    customer_name = customer.name if customer else "A customer"
    notify_admins(
        ticket.id,
        f"New ticket #{ticket.id} from {customer_name}: {title[:80]}",
        exclude_user_id=user_id,
    )

    db.session.commit()

    return jsonify({"message": "Ticket created", "ticket": ticket_to_dict(ticket)}), 201


@tickets_bp.route("", methods=["GET"])
@jwt_required()
def my_tickets():
    user_id = int(get_jwt_identity())
    tickets = (
        Ticket.query.filter_by(user_id=user_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return jsonify([ticket_to_dict(t) for t in tickets])


@tickets_bp.route("/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id):
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    # Customers can open only their own tickets. Admins can open any.
    if role != "admin" and ticket.user_id != user_id:
        return jsonify({"error": "You do not have access to this ticket"}), 403

    # Opening a ticket marks its notifications as read for this person
    Notification.query.filter_by(
        user_id=user_id, ticket_id=ticket_id, is_read=False
    ).update({"is_read": True})
    db.session.commit()

    messages = (
        Message.query.filter_by(ticket_id=ticket_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    attachments = Attachment.query.filter_by(ticket_id=ticket_id).all()

    message_list = []
    for m in messages:
        sender = db.session.get(User, m.sender_id)
        message_list.append(
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_name": sender.name if sender else "Unknown",
                "sender_role": sender.role if sender else None,
                "text": m.text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
        )

    attachment_list = [
        {"id": a.id, "file_url": a.file_url, "file_type": a.file_type}
        for a in attachments
    ]

    result = ticket_to_dict(ticket)
    customer = db.session.get(User, ticket.user_id)
    result["customer_name"] = customer.name if customer else "Unknown"
    result["customer_email"] = customer.email if customer else None
    result["messages"] = message_list
    result["attachments"] = attachment_list
    return jsonify(result)