import os
import urllib.parse
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import text

from extensions import db
import models  # noqa: F401  (this loads the tables)
from auth import auth_bp
from tickets import tickets_bp
from uploads import uploads_bp
from messages import messages_bp
from admin import admin_bp
from notifications import notifications_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(notifications_bp)
CORS(app)

db_user = os.getenv("DB_USER")
db_password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", ""))
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

# File uploads
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB per request
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
JWTManager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(admin_bp)

with app.app_context():
    db.create_all()


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "Upload is too large (max 100 MB per request)"}), 413


@app.route("/")
def home():
    return jsonify({"message": "Customer Ticket Raise API is running"})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "Customer Ticket Raise"})


@app.route("/api/db-test")
def db_test():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"database": "connected"})
    except Exception as e:
        return jsonify({"database": "error", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)