import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from extensions import db
from models import Attachment, Ticket

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api")

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "mkv"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 5


def get_extension(filename):
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def get_file_size(file):
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size


@uploads_bp.route("/tickets/<int:ticket_id>/attachments", methods=["POST"])
@jwt_required()
def upload_attachments(ticket_id):
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    if role != "admin" and ticket.user_id != user_id:
        return jsonify({"error": "You do not have access to this ticket"}), 403

    files = request.files.getlist("files")
    files = [f for f in files if f and f.filename]

    if not files:
        return jsonify({"error": "No files received. Use the field name 'files'"}), 400
    if len(files) > MAX_FILES_PER_UPLOAD:
        return jsonify({"error": f"You can upload at most {MAX_FILES_PER_UPLOAD} files at once"}), 400

    # Check every file first, so we never save only some of them
    checked = []
    for f in files:
        ext = get_extension(f.filename)
        size = get_file_size(f)

        if ext in IMAGE_EXTENSIONS:
            file_type, max_bytes = "image", MAX_IMAGE_BYTES
        elif ext in VIDEO_EXTENSIONS:
            file_type, max_bytes = "video", MAX_VIDEO_BYTES
        else:
            return jsonify({"error": f"File type not allowed: {f.filename}"}), 400

        if size == 0:
            return jsonify({"error": f"File is empty: {f.filename}"}), 400
        if size > max_bytes:
            limit_mb = max_bytes // (1024 * 1024)
            return jsonify({"error": f"{f.filename} is too large (max {limit_mb} MB for {file_type}s)"}), 400

        checked.append((f, ext, file_type))

    saved = []
    for f, ext, file_type in checked:
        new_name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(current_app.config["UPLOAD_FOLDER"], new_name))

        attachment = Attachment(
            ticket_id=ticket_id,
            file_url=f"/api/files/{new_name}",
            file_type=file_type,
        )
        db.session.add(attachment)
        saved.append(attachment)

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Files uploaded",
                "attachments": [
                    {"id": a.id, "file_url": a.file_url, "file_type": a.file_type}
                    for a in saved
                ],
            }
        ),
        201,
    )


@uploads_bp.route("/files/<path:filename>", methods=["GET"])
def serve_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)