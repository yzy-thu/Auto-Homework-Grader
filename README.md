**English** | [中文](./README.zh.md)

# Auto Homework Grader

A web-based automatic homework grading application. Upload standard answers (images/PDF) and student submissions (folder path or ZIP upload), and the system automatically recognizes content (PDF/Markdown/images), calls the Gemini API for comparison grading (5 concurrent), displays real-time progress, supports mid-process pausing, and exports a CSV grade sheet.

## Tech Stack

- **Frontend**: Vue 3 + Vite
- **Backend**: Python Flask
- **AI**: Google Gemini API
- **Communication**: SSE (Server-Sent Events) for real-time progress, with auto-reconnection

## Quick Start

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Configure API Key

Edit `backend/.env` with your Gemini API Key:

```
GEMINI_API_KEY=your_api_key_here
```

### 3. Start Services

```bash
# Terminal 1 — Start backend (port 5001)
cd backend
python app.py

# Terminal 2 — Start frontend (port 3000)
cd frontend
npm run dev
```

Open your browser at `http://localhost:3000`.

## Usage

1. **Upload Standard Answers**: Drag files into the upload area, or click "Browse Files" to select files (supports images and PDF)
2. **Specify Student Submissions**: Two options available
   - **Folder Path**: Enter the absolute path to the folder containing student submissions
   - **Upload ZIP**: Drag or select a ZIP file containing all student submissions
3. **Set Grading Rules**: Describe your grading criteria in the text box (e.g., total points, deduction rules)
4. **Start Grading**: Click "Start Grading" — the system processes submissions with 5 concurrent workers
5. **Monitor Progress**: Watch the real-time progress bar and log output
6. **Pause (Optional)**: Click "Stop" to pause mid-process — completed results are preserved and exportable
7. **Download Results**: After grading completes (or is paused), click "Download CSV" to get the grade sheet

## Student Submission Filenames

The student folder can contain a mix of ZIP files and loose PDF/image files — the system handles both.

### Smart Filename Parsing

The system uses a two-tier strategy to extract student info from filenames:

1. **Default Rules** (no Gemini call): Recognizes `StudentID_Name_Random.ext` format
   - e.g., `2024001_Alice_12345.zip`, `2020080089_Bob_1920.pdf`
   - Used automatically when ≥80% of files match this pattern

2. **Gemini Smart Parsing** (automatic fallback): When most filenames don't match the default format, Gemini is called once to analyze all filenames and automatically identify field structure (e.g., student ID, name, class, date, etc.)

### Dynamic CSV Columns

CSV output columns are determined by the filename parsing results. Metadata columns come first, with **Score and Feedback always as the last two columns**. Example:

| Student ID | Name | Score | Feedback | Error |
|------------|------|-------|----------|-------|
| 2024001 | Alice | 95 | Complete solution... | |

## Supported File Formats

- **Images**: PNG, JPG, JPEG, GIF, BMP, WebP
- **Documents**: PDF, Markdown (.md), TXT

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload-answers` | POST | Upload standard answer files, returns `session_id` |
| `/api/upload-submissions` | POST | Upload student submissions ZIP, extracts and returns folder path |
| `/api/grade` | POST | Start grading job (5 concurrent), returns `job_id` |
| `/api/grade/stream?job_id=` | GET | SSE stream for real-time progress (supports reconnection) |
| `/api/grade/stop` | POST | Pause grading job, preserves completed results |
| `/api/download?job_id=` | GET | Download CSV grade file (available after completion or pause) |

## Error Handling

- Corrupted ZIP files: Skipped with error logged, continues to next student
- No homework files: Logged and skipped
- Gemini API errors: Auto-retry up to 5 times with exponential backoff (2s → 4s → 8s → 16s → 32s), covering rate limits, server errors, network timeouts, etc.
- Oversized files: Files over 20MB are skipped
- Nested ZIPs: Automatically extracted recursively (depth limit: 2)
- SSE disconnection: Frontend auto-reconnects, backend replays missed events — no data loss

## Project Structure

```
num_analysis/
├── backend/
│   ├── app.py                 # Flask entry point (port 5001)
│   ├── config.py              # Configuration (env vars, paths, model name)
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # GEMINI_API_KEY
│   ├── services/
│   │   ├── zip_extractor.py   # ZIP extraction + Chinese encoding (UTF-8/GBK)
│   │   ├── file_processor.py  # File detection + Gemini Part conversion
│   │   ├── gemini_grader.py   # Gemini grading + filename analysis + retries
│   │   └── csv_exporter.py    # CSV generation (dynamic columns + UTF-8 BOM)
│   ├── routes/
│   │   ├── grading.py         # Grading endpoints (parallel + pause)
│   │   └── upload.py          # Answer upload + submission ZIP upload
│   └── utils/
│       └── sse.py             # SSE formatting utility (with event IDs)
├── frontend/
│   ├── package.json
│   ├── vite.config.js         # Proxy to Flask port 5001
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── components/
│       │   ├── GradingForm.vue     # Input form (drag & drop / file picker)
│       │   ├── ProgressTracker.vue # Progress bar + live log + stop button
│       │   └── ResultsTable.vue    # Dynamic column results table + CSV download
│       ├── composables/
│       │   ├── useGrading.js       # SSE connection + state management + pause
│       │   └── useFileUpload.js    # File upload logic (with progress bar)
│       └── assets/
│           └── style.css
└── .gitignore
```
