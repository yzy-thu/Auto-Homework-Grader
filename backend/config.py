import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDOoZS3pXo0TIZM1KJstRe_dDqr5Oc3x1w")
GEMINI_MODEL = "gemini-3-flash-preview"

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "grading_app")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_ZIP_DEPTH = 2

SSE_KEEPALIVE_INTERVAL = 15  # seconds

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
ALLOWED_DOC_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}
ALL_SUPPORTED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS
