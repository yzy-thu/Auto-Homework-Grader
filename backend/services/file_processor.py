import os
import mimetypes

from google.genai import types

from config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_DOC_EXTENSIONS,
    ALL_SUPPORTED_EXTENSIONS,
    MAX_FILE_SIZE,
)


MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


def find_homework_files(directory):
    """Recursively find all supported homework files in a directory.

    Returns list of absolute file paths, sorted by name.
    """
    results = []
    for root, _dirs, files in os.walk(directory):
        # Skip __MACOSX and hidden directories
        if "__MACOSX" in root or os.path.basename(root).startswith("."):
            continue
        for fname in files:
            if fname.startswith("."):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in ALL_SUPPORTED_EXTENSIONS:
                full_path = os.path.join(root, fname)
                if os.path.getsize(full_path) <= MAX_FILE_SIZE:
                    results.append(full_path)
    return sorted(results)


def file_to_gemini_part(file_path):
    """Convert a file to a Gemini Part object.

    For text files (md, txt), returns the text content as a string.
    For binary files (pdf, images), returns a Part with inline data.
    """
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = MIME_MAP.get(ext)
    if not mime_type:
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    # Text files: return content as string
    if ext in {".md", ".markdown", ".txt"}:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return types.Part.from_text(text=f"[File: {os.path.basename(file_path)}]\n{content}")

    # Binary files (PDF, images): return as inline data
    with open(file_path, "rb") as f:
        data = f.read()

    return types.Part.from_bytes(data=data, mime_type=mime_type)
