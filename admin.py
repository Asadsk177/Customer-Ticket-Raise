from functools import wraps

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import func, or_

from extensions import db
from models import Ticket, User
from notifications import notify
from permissions import current_role
from tickets import CATEGORIES, PRIORITIES, ticket_to_dict

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

STATUSES = ["Open", "In Progress", "Resolved"]
ROLES = ["customer", "admin"]


def admin_required(fn):
    """Allows only logged-in users who are admins in the database right now."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if current_role() != "admin":
            return jsonify({"error": "Admin access only"}), 403
        return fn(*args, **kwargs)

    return wrapper


def user_to_dict(u):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


# ---------- Tickets ----------


@admin_bp.route("/tickets", methods=["GET"])
@admin_required
def all_tickets():
    query = Ticket.query

    status = request.args.get("status")
    category = request.args.get("category")
    priority = request.args.get("priority")
    search = (request.args.get("search") or "").strip()

    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if priority:
        query = query.filter_by(priority=priority)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Ticket.title.ilike(like), Ticket.description.ilike(like))
        )

    tickets = query.order_by(Ticket.created_at.desc()).all()

    result = []
    for t in tickets:
        item = ticket_to_dict(t)
        customer = db.session.get(User, t.user_id)
        item["customer_name"] = customer.name if customer else "Unknown"
        item["customer_email"] = customer.email if customer else None
        result.append(item)

    return jsonify(result)


@admin_bp.route("/tickets/<int:ticket_id>/status", methods=["PATCH"])
@admin_required
def update_status(ticket_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in STATUSES:
        return jsonify({"error": f"status must be one of {STATUSES}"}), 400

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    old_status = ticket.status
    ticket.status = new_status
    if old_status != new_status:
        notify(ticket.user_id, ticket.id, f'Your ticket #{ticket.id} is now "{new_status}"')
    db.session.commit()

    return jsonify({"message": "Status updated", "ticket": ticket_to_dict(ticket)})


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def stats():
    rows = db.session.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    counts = {s: 0 for s in STATUSES}
    for status, count in rows:
        counts[status] = count

    return jsonify(
        {
            "total": sum(counts.values()),
            "by_status": counts,
            "categories": CATEGORIES,
            "priorities": PRIORITIES,
        }
    )


# ---------- Team and users ----------


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    query = User.query

    role = request.args.get("role")
    search = (request.args.get("search") or "").strip()

    if role in ROLES:
        query = query.filter_by(role=role)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like)))

    users = query.order_by(User.created_at.desc()).all()
    return jsonify([user_to_dict(u) for u in users])


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or "admin"

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if "@" not in email:
        return jsonify({"error": "Enter a valid email"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if len(password.encode("utf-8")) > 72:
        return jsonify({"error": "Password is too long (max 72 characters)"}), 400
    if role not in ROLES:
        return jsonify({"error": f"role must be one of {ROLES}"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "This email is already registered"}), 409

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(name=name, email=email, password_hash=hashed, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created", "user": user_to_dict(user)}), 201


@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@admin_required
def change_role(user_id):
    my_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    new_role = data.get("role")

    if new_role not in ROLES:
        return jsonify({"error": f"role must be one of {ROLES}"}), 400
    if user_id == my_id:
        return jsonify({"error": "You cannot change your own role"}), 400

    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    target.role = new_role
    db.session.commit()

    return jsonify({"message": "Role updated", "user": user_to_dict(target)})