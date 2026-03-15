import os
import zipfile
import shutil

from config import MAX_ZIP_DEPTH


def _decode_zip_filename(info):
    """Decode ZIP entry filename, handling Chinese encoding (CP437 -> UTF-8/GBK)."""
    if info.flag_bits & (1 << 11):
        # UTF-8 flag is set, filename is already UTF-8
        return info.filename
    try:
        raw = info.filename.encode("cp437")
    except UnicodeEncodeError:
        return info.filename
    # Try UTF-8 first, then GBK
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return info.filename


def extract_zip(zip_path, dest_dir, depth=0):
    """Extract a ZIP file to dest_dir, handling Chinese filenames and nested ZIPs.

    Returns:
        list of extracted file paths (absolute).
    Raises:
        zipfile.BadZipFile if the ZIP is corrupted.
    """
    if depth > MAX_ZIP_DEPTH:
        return []

    os.makedirs(dest_dir, exist_ok=True)
    extracted_files = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            decoded_name = _decode_zip_filename(info)
            # Sanitize path to prevent zip slip
            decoded_name = decoded_name.lstrip("/").lstrip("\\")
            if ".." in decoded_name:
                continue

            target_path = os.path.join(dest_dir, decoded_name)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            with zf.open(info) as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            extracted_files.append(target_path)

    # Handle nested ZIPs
    nested_zips = [f for f in extracted_files if f.lower().endswith(".zip")]
    for nested_zip in nested_zips:
        nested_dest = nested_zip + "_extracted"
        try:
            nested_files = extract_zip(nested_zip, nested_dest, depth + 1)
            extracted_files.extend(nested_files)
        except zipfile.BadZipFile:
            pass
        finally:
            # Remove the nested zip after extraction attempt
            if os.path.exists(nested_zip):
                os.remove(nested_zip)

    return [f for f in extracted_files if os.path.exists(f)]


def parse_submission_filename(filename):
    """Parse student info from submission filename using default convention.

    Expected format: 学号_姓名_随机数.ext or 学号_姓名.ext
    Returns dict {"学号": ..., "姓名": ...} or None if format doesn't match.
    """
    stem = os.path.splitext(filename)[0]
    parts = stem.split("_")
    if len(parts) >= 2 and len(parts[0]) >= 4:
        return {"学号": parts[0], "姓名": parts[1]}
    return None


def default_parse_works(filenames):
    """Check if the default filename convention works for most files.

    Returns True if >= 80% of filenames can be parsed by the default parser.
    """
    if not filenames:
        return True
    success = sum(1 for fn in filenames if parse_submission_filename(fn) is not None)
    return success / len(filenames) >= 0.8
