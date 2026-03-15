import time
import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


class GradeResult(BaseModel):
    score: float
    feedback: str


class ParsedFile(BaseModel):
    filename: str
    values: list[str]


class FilenameAnalysis(BaseModel):
    columns: list[str]
    files: list[ParsedFile]


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


RETRYABLE_KEYWORDS = [
    "429", "resource_exhausted", "rate",           # rate limit
    "500", "503", "internal", "unavailable",       # server errors
    "overloaded", "capacity",                      # busy
    "timeout", "timed out", "deadline",            # timeout
    "connection", "network", "reset", "broken",    # network errors
    "ssl", "eof",                                  # transport errors
]


def _is_retryable(error):
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    return any(kw in error_str for kw in RETRYABLE_KEYWORDS)


def grade_student(answer_parts, homework_parts, grading_prompt, max_retries=5):
    """Call Gemini to grade a student's homework against the answer key.

    Retries on transient errors (rate limit, server errors, network issues)
    with exponential backoff: 2s, 4s, 8s, 16s, 32s.

    Args:
        answer_parts: list of Gemini Part objects for the standard answer.
        homework_parts: list of Gemini Part objects for the student's homework.
        grading_prompt: user-defined grading instructions/rubric.
        max_retries: max retry attempts on transient errors.

    Returns:
        GradeResult with score and feedback.

    Raises:
        Exception if all retries are exhausted or error is non-retryable.
    """
    client = _get_client()

    system_instruction = (
        "You are a teaching assistant grading student homework. "
        "Compare the student's submission against the provided standard answer. "
        "Follow the grading rules specified by the instructor. "
        "Be fair, consistent, and provide constructive feedback in Chinese. "
        "Return your evaluation as JSON with 'score' (numeric) and 'feedback' (string)."
    )

    contents = []
    contents.append(types.Part.from_text(text="=== 标准答案 (Standard Answer) ==="))
    contents.extend(answer_parts)
    contents.append(types.Part.from_text(text="=== 学生作业 (Student Homework) ==="))
    contents.extend(homework_parts)
    contents.append(types.Part.from_text(text=f"=== 评分规则 (Grading Rules) ===\n{grading_prompt}"))

    last_error = None
    for attempt in range(max_retries):
        try:
            start = time.time()
            logger.info("Calling Gemini API (attempt %d/%d)...", attempt + 1, max_retries)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=GradeResult,
                    temperature=0.1,
                ),
            )

            elapsed = time.time() - start
            result = json.loads(response.text)
            grade = GradeResult(**result)
            logger.info("Gemini responded in %.1fs — score: %s, feedback: %s",
                        elapsed, grade.score, grade.feedback[:80])
            return grade

        except Exception as e:
            elapsed = time.time() - start
            last_error = e

            if _is_retryable(e) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s, 16s, 32s
                logger.warning("Retryable error (%.1fs), retry %d/%d in %ds: %s",
                               elapsed, attempt + 1, max_retries, wait_time, e)
                time.sleep(wait_time)
                continue
            else:
                logger.error("Gemini error (%.1fs, attempt %d/%d): %s",
                             elapsed, attempt + 1, max_retries, e)
                if not _is_retryable(e):
                    raise

    raise last_error


def analyze_filenames(filenames, max_retries=3):
    """Use Gemini to parse a list of filenames into structured columns.

    Args:
        filenames: list of filename strings (e.g. ["2024001_张三_12345.pdf", ...])

    Returns:
        FilenameAnalysis with columns (list of column names) and
        files (list of ParsedFile with values in same order as columns).
    """
    client = _get_client()

    system_instruction = (
        "You are a data parsing assistant. Analyze the given list of filenames "
        "and extract structured metadata from them. "
        "Determine what fields are encoded in the filenames (e.g. student ID, name, class, date, etc.). "
        "Return the column names in Chinese and the parsed values for each file. "
        "Column names should be descriptive (e.g. '学号', '姓名', '班级'). "
        "If a field is not present or is a meaningless random number, you may omit it. "
        "Keep only meaningful metadata columns. Do NOT include file extensions. "
        "Do NOT include 'score' or 'feedback' columns — those will be added separately."
    )

    prompt = "Please parse these filenames and extract structured fields:\n\n"
    for fn in filenames:
        prompt += f"- {fn}\n"

    last_error = None
    for attempt in range(max_retries):
        try:
            start = time.time()
            logger.info("Analyzing %d filenames with Gemini (attempt %d/%d)...",
                        len(filenames), attempt + 1, max_retries)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=FilenameAnalysis,
                    temperature=0,
                ),
            )

            elapsed = time.time() - start
            result = json.loads(response.text)
            analysis = FilenameAnalysis(**result)
            logger.info("Filename analysis done in %.1fs — %d columns: %s",
                        elapsed, len(analysis.columns), analysis.columns)
            return analysis

        except Exception as e:
            elapsed = time.time() - start
            last_error = e
            if _is_retryable(e) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                logger.warning("Retryable error analyzing filenames (%.1fs), retry in %ds: %s",
                               elapsed, wait_time, e)
                time.sleep(wait_time)
                continue
            else:
                logger.error("Filename analysis error (%.1fs): %s", elapsed, e)
                if not _is_retryable(e):
                    raise

    raise last_error
