import os
import uuid
import logging

from flask import Blueprint, request, jsonify

from config import UPLOAD_DIR
from services.zip_extractor import extract_zip

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/api/upload-answers", methods=["POST"])
def upload_answers():
    """Upload standard answer screenshots.

    Accepts multipart form with one or more files under the 'files' key.
    Returns a session_id for later reference.
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    session_id = str(uuid.uuid4())
    answer_dir = os.path.join(UPLOAD_DIR, session_id, "answers")
    os.makedirs(answer_dir, exist_ok=True)

    saved = []
    for f in files:
        if f.filename:
            safe_name = os.path.basename(f.filename)
            dest = os.path.join(answer_dir, safe_name)
            f.save(dest)
            saved.append(safe_name)

    if not saved:
        return jsonify({"error": "No valid files uploaded"}), 400

    return jsonify({
        "session_id": session_id,
        "files": saved,
        "count": len(saved),
    })


@upload_bp.route("/api/upload-submissions", methods=["POST"])
def upload_submissions():
    """Upload a ZIP file containing student submissions.

    Extracts the ZIP and returns the folder path for grading.
    The ZIP should contain student files (PDFs, images, nested ZIPs)
    at the top level or inside a single root folder.
    """
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file uploaded"}), 400

    if not f.filename.lower().endswith(".zip"):
        return jsonify({"error": "Only ZIP files are accepted"}), 400

    upload_id = str(uuid.uuid4())
    upload_dir = os.path.join(UPLOAD_DIR, upload_id, "submissions")
    os.makedirs(upload_dir, exist_ok=True)

    # Save the ZIP temporarily
    zip_path = os.path.join(upload_dir, "uploaded.zip")
    f.save(zip_path)

    # Extract
    try:
        extract_dir = os.path.join(upload_dir, "extracted")
        extract_zip(zip_path, extract_dir)
    except Exception as e:
        logger.error("Failed to extract submissions ZIP: %s", e)
        return jsonify({"error": f"Failed to extract ZIP: {e}"}), 400
    finally:
        # Remove the original ZIP to save space
        if os.path.exists(zip_path):
            os.remove(zip_path)

    # If the ZIP contains a single root folder, use that as the submissions dir
    entries = [e for e in os.listdir(extract_dir) if not e.startswith(".") and e != "__MACOSX"]
    if len(entries) == 1:
        single = os.path.join(extract_dir, entries[0])
        if os.path.isdir(single):
            extract_dir = single

    # Count files found
    file_count = len([
        name for name in os.listdir(extract_dir)
        if os.path.isfile(os.path.join(extract_dir, name)) and not name.startswith(".")
    ])

    logger.info("Extracted submissions ZIP to %s (%d files)", extract_dir, file_count)

    return jsonify({
        "folder_path": extract_dir,
        "file_count": file_count,
    })
