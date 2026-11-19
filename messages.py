from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from extensions import db
from models import Message, Ticket, User
from notifications import notify, notify_admins

messages_bp = Blueprint("messages", __name__, url_prefix="/api/tickets")


@messages_bp.route("/<int:ticket_id>/messages", methods=["POST"])
@jwt_required()
def add_message(ticket_id):
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    # Customers can write only on their own tickets. Admins can write on any.
    if role != "admin" and ticket.user_id != user_id:
        return jsonify({"error": "You do not have access to this ticket"}), 403

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Message text is required"}), 400
    if len(text) > 5000:
        return jsonify({"error": "Message is too long (max 5000 characters)"}), 400

    message = Message(ticket_id=ticket_id, sender_id=user_id, text=text)
    db.session.add(message)

    sender = db.session.get(User, user_id)
    preview = text if len(text) <= 60 else text[:57] + "..."

    if role == "admin":
        if ticket.user_id != user_id:
            notify(ticket.user_id, ticket.id, f'Support replied on ticket #{ticket.id}: "{preview}"')
    else:
        name = sender.name if sender else "A customer"
        notify_admins(
            ticket.id,
            f'{name} sent a message on ticket #{ticket.id}: "{preview}"',
            exclude_user_id=user_id,
        )

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Message sent",
                "data": {
                    "id": message.id,
                    "sender_id": user_id,
                    "sender_name": sender.name if sender else "Unknown",
                    "sender_role": sender.role if sender else None,
                    "text": message.text,
                    "created_at": message.created_at.isoformat() if message.created_at else None,
                },
            }
        ),
        201,
    )