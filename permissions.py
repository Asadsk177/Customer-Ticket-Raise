from flask_jwt_extended import get_jwt_identity

from extensions import db
from models import User


def current_role():
    """The logged-in user's role as stored in the database right now."""
    user = db.session.get(User, int(get_jwt_identity()))
    return user.role if user else None