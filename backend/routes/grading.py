import os
import glob
import uuid
import threading
import queue
import time
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, request, jsonify, Response

from config import UPLOAD_DIR, SSE_KEEPALIVE_INTERVAL, ALL_SUPPORTED_EXTENSIONS
from services.zip_extractor import extract_zip, parse_submission_filename, default_parse_works
from services.file_processor import find_homework_files, file_to_gemini_part
from services.gemini_grader import grade_student, analyze_filenames
from services.csv_exporter import export_csv
from utils.sse import sse_event, sse_keepalive

grading_bp = Blueprint("grading", __name__)

# In-memory store for job queues and results
_jobs = {}  # job_id -> {"queue": Queue, "results": [], "csv_path": str, "status": str}


def _emit(job, event_type, data):
    """Push an SSE event to both the live queue and the replay history."""
    job["queue"].put((event_type, data))
    job["history"].append((event_type, data))


def _grade_worker(job_id, session_id, student_folder, grading_prompt):
    """Background worker that processes all student ZIPs and pushes SSE events."""
    job = _jobs[job_id]

    # Load answer files
    answer_dir = os.path.join(UPLOAD_DIR, session_id, "answers")
    if not os.path.isdir(answer_dir):
        _emit(job,"error", {"message": "Answer files not found. Please upload answers first."})
        _emit(job,"complete", {"total": 0, "graded": 0})
        job["status"] = "complete"
        return

    answer_files = []
    for root, _dirs, files in os.walk(answer_dir):
        for fname in sorted(files):
            answer_files.append(os.path.join(root, fname))

    if not answer_files:
        _emit(job,"error", {"message": "No answer files found in upload."})
        _emit(job,"complete", {"total": 0, "graded": 0})
        job["status"] = "complete"
        return

    answer_parts = []
    for af in answer_files:
        try:
            answer_parts.append(file_to_gemini_part(af))
        except Exception as e:
            _emit(job,"error", {"message": f"Failed to process answer file {os.path.basename(af)}: {e}"})

    if not answer_parts:
        _emit(job,"error", {"message": "Could not process any answer files."})
        _emit(job,"complete", {"total": 0, "graded": 0})
        job["status"] = "complete"
        return

    # Find all student submissions (ZIPs + loose files like PDFs)
    if not os.path.isdir(student_folder):
        _emit(job,"error", {"message": f"Student folder not found: {student_folder}"})
        _emit(job,"complete", {"total": 0, "graded": 0})
        job["status"] = "complete"
        return

    # Collect submissions: each entry is (filename, type)
    #   type = "zip" or "file"
    submissions = []
    for fname in sorted(os.listdir(student_folder)):
        fpath = os.path.join(student_folder, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext == ".zip":
            submissions.append((fname, "zip"))
        elif ext in ALL_SUPPORTED_EXTENSIONS:
            submissions.append((fname, "file"))

    total = len(submissions)

    if total == 0:
        _emit(job,"error", {"message": f"No student submissions found in: {student_folder}"})
        _emit(job,"complete", {"total": 0, "graded": 0})
        job["status"] = "complete"
        return

    _emit(job, "progress", {"message": f"Found {total} student submissions", "current": 0, "total": total})

    # --- Parse filenames: try default convention first, fall back to Gemini ---
    all_fnames = [fn for fn, _ in submissions]
    use_default = default_parse_works(all_fnames)

    if use_default:
        columns = ["学号", "姓名"]
        # Build metadata map: filename -> dict
        meta_map = {}
        for fn in all_fnames:
            parsed = parse_submission_filename(fn)
            if parsed:
                meta_map[fn] = parsed
            else:
                stem = os.path.splitext(fn)[0]
                meta_map[fn] = {"学号": stem, "姓名": ""}
        _emit(job, "progress", {"message": "Filename format recognized (default convention)", "current": 0, "total": total})
    else:
        _emit(job, "progress", {"message": "Non-standard filenames detected, calling Gemini to analyze...", "current": 0, "total": total})
        try:
            analysis = analyze_filenames(all_fnames)
            columns = list(analysis.columns)
            meta_map = {}
            for pf in analysis.files:
                meta = {}
                for i, col in enumerate(columns):
                    meta[col] = pf.values[i] if i < len(pf.values) else ""
                meta_map[pf.filename] = meta
            # Files not in Gemini response get empty metadata
            for fn in all_fnames:
                if fn not in meta_map:
                    meta_map[fn] = {col: "" for col in columns}
            _emit(job, "progress", {"message": f"Filename analysis complete. Columns: {', '.join(columns)}", "current": 0, "total": total})
        except Exception as e:
            # Fallback: use filename as single column
            _emit(job, "error", {"message": f"Filename analysis failed ({e}), using filenames as-is"})
            columns = ["文件名"]
            meta_map = {fn: {"文件名": os.path.splitext(fn)[0]} for fn in all_fnames}

    job["columns"] = columns
    _emit(job, "columns", {"columns": columns})

    results = []
    results_lock = threading.Lock()
    completed_count = [0]  # mutable counter shared across threads
    work_dir = os.path.join(UPLOAD_DIR, job_id, "work")

    def grade_one(fname, sub_type):
        meta = meta_map.get(fname, {})
        display_name = " ".join(str(v) for v in meta.values() if v)
        file_path = os.path.join(student_folder, fname)

        _emit(job, "progress", {
            "message": f"Processing: {display_name or fname}",
            "current": completed_count[0],
            "total": total,
        })

        result = {
            "meta": meta,
            "score": "",
            "feedback": "",
            "error": "",
        }

        try:
            if sub_type == "zip":
                extract_dest = os.path.join(work_dir, student_id)
                extract_zip(file_path, extract_dest)
                hw_files = find_homework_files(extract_dest)
            else:
                hw_files = [file_path]

            if not hw_files:
                result["error"] = "No homework files found in submission"
                return result

            hw_parts = []
            for hf in hw_files:
                try:
                    hw_parts.append(file_to_gemini_part(hf))
                except Exception as e:
                    _emit(job, "progress", {
                        "message": f"Warning: could not process {os.path.basename(hf)}: {e}",
                        "current": completed_count[0],
                        "total": total,
                    })

            if not hw_parts:
                result["error"] = "Could not process any homework files"
                return result

            grade = grade_student(answer_parts, hw_parts, grading_prompt)
            result["score"] = grade.score
            result["feedback"] = grade.feedback

        except zipfile.BadZipFile:
            result["error"] = "Corrupted ZIP file"
        except Exception as e:
            result["error"] = str(e)
        finally:
            if sub_type == "zip":
                student_work = os.path.join(work_dir, student_id)
                if os.path.exists(student_work):
                    shutil.rmtree(student_work, ignore_errors=True)

        return result

    stopped = job["stopped"]
    was_stopped = False

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(grade_one, fname, sub_type): (fname, sub_type)
            for fname, sub_type in submissions
        }
        for future in as_completed(futures):
            if stopped.is_set():
                # Cancel remaining futures
                for f in futures:
                    f.cancel()
                was_stopped = True
                break
            result = future.result()
            with results_lock:
                completed_count[0] += 1
                current = completed_count[0]
                results.append(result)
            # Flatten meta for SSE event
            flat = {**result.get("meta", {}), "score": result["score"], "feedback": result["feedback"], "error": result["error"]}
            _emit(job, "result", {**flat, "current": current, "total": total})

    # Sort results by first metadata column for consistent CSV output
    first_col = columns[0] if columns else ""
    results.sort(key=lambda r: r.get("meta", {}).get(first_col, ""))

    # Generate CSV (full or partial)
    csv_path = os.path.join(UPLOAD_DIR, job_id, "grades.csv")
    export_csv(results, csv_path, columns=columns)
    job["csv_path"] = csv_path
    job["results"] = results

    graded = len([r for r in results if r["score"] != ""])

    if was_stopped:
        job["status"] = "stopped"
        _emit(job, "stopped", {"total": total, "graded": graded})
    else:
        job["status"] = "complete"
        _emit(job, "complete", {"total": total, "graded": graded})

    # Clean up work directory
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)


@grading_bp.route("/api/grade", methods=["POST"])
def start_grading():
    """Start a grading job.

    Expects JSON: {session_id, student_folder, grading_prompt}
    Returns: {job_id}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    session_id = data.get("session_id")
    student_folder = data.get("student_folder")
    grading_prompt = data.get("grading_prompt", "")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not student_folder:
        return jsonify({"error": "student_folder is required"}), 400

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "queue": queue.Queue(),
        "results": [],
        "history": [],   # all SSE events for replay on reconnect
        "csv_path": None,
        "status": "running",
        "stopped": threading.Event(),  # set to signal stop
    }

    thread = threading.Thread(
        target=_grade_worker,
        args=(job_id, session_id, student_folder, grading_prompt),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@grading_bp.route("/api/grade/stream")
def grade_stream():
    """SSE stream for grading progress.

    Query param: job_id
    Supports reconnection via Last-Event-ID header — replays missed events.
    Events: progress, result, error, complete
    """
    job_id = request.args.get("job_id")
    if not job_id or job_id not in _jobs:
        return jsonify({"error": "Invalid job_id"}), 400

    # On reconnect, EventSource sends Last-Event-ID so we can resume
    last_id = request.headers.get("Last-Event-ID", type=int, default=0)

    def generate():
        job = _jobs[job_id]
        q = job["queue"]
        event_id = 0

        # Replay any events the client missed (from history)
        for event_type, data in job["history"]:
            event_id += 1
            if event_id <= last_id:
                continue
            yield sse_event(event_type, data, event_id)
            if event_type in ("complete", "stopped"):
                return

        # Continue streaming new events from the queue
        while True:
            try:
                event_type, data = q.get(timeout=SSE_KEEPALIVE_INTERVAL)
                event_id += 1
                yield sse_event(event_type, data, event_id)

                if event_type in ("complete", "stopped"):
                    break
            except queue.Empty:
                yield sse_keepalive()
                if job["status"] in ("complete", "stopped") and q.empty():
                    break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@grading_bp.route("/api/grade/stop", methods=["POST"])
def stop_grading():
    """Stop a running grading job. Already-graded results are preserved."""
    data = request.get_json() or {}
    job_id = data.get("job_id") or request.args.get("job_id")
    if not job_id or job_id not in _jobs:
        return jsonify({"error": "Invalid job_id"}), 400

    job = _jobs[job_id]
    if job["status"] != "running":
        return jsonify({"error": "Job is not running"}), 400

    job["stopped"].set()
    return jsonify({"ok": True})


@grading_bp.route("/api/download")
def download_csv():
    """Download the grading CSV file."""
    job_id = request.args.get("job_id")
    if not job_id or job_id not in _jobs:
        return jsonify({"error": "Invalid job_id"}), 400

    job = _jobs[job_id]
    csv_path = job.get("csv_path")

    if not csv_path or not os.path.exists(csv_path):
        return jsonify({"error": "CSV file not ready yet"}), 404

    from flask import send_file
    return send_file(
        csv_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="grades.csv",
    )
