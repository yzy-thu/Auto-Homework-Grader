import os
import shutil
import atexit
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from flask import Flask
from flask_cors import CORS

from config import UPLOAD_DIR
from routes.upload import upload_bp
from routes.grading import grading_bp


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB
    CORS(app)

    app.register_blueprint(upload_bp)
    app.register_blueprint(grading_bp)

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    return app


def cleanup():
    """Clean up temporary files on exit."""
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)


atexit.register(cleanup)

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True, threaded=True)
