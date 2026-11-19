import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if "@" not in email:
        return jsonify({"error": "Enter a valid email"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if len(password.encode("utf-8")) > 72:
        return jsonify({"error": "Password is too long (max 72 characters)"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "This email is already registered"}), 409

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(name=name, email=email, password_hash=hashed, role="customer")
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Account created", "user_id": user.id}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(
        identity=str(user.id), additional_claims={"role": user.role}
    )
    return jsonify(
        {
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            },
        }
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(
        {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
    )