"""
config.py - Central configuration for the AI Agent.
Reads settings from .env file and environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Project Root ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()

# Auto-load .env file from project root (if it exists)
load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Groq LLM ──────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
# Preferred models in priority order (agent will fall back if one fails)
# These are the models available on this Groq account
GROQ_MODELS = [
    "qwen/qwen3.6-27b",
    "groq/compound",
    "groq/compound-mini",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
]
GROQ_TEMPERATURE = 0.7
GROQ_MAX_TOKENS = 4096

# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_FILE = BASE_DIR / "credentials.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

# Optional: set this to an existing Google Sheet ID to write into it directly
# instead of creating a new sheet each run.
# The sheet must be shared with the service account as Editor:
#   dilkash@gen-lang-client-0065720801.iam.gserviceaccount.com
# Leave empty ("") to always create a new spreadsheet.
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

# ── Excel ─────────────────────────────────────────────────────────────────────
# Possible Excel executable paths on Windows
EXCEL_PATHS = [
    r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
    r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
    r"C:\Program Files\Microsoft Office\Office15\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\Office15\EXCEL.EXE",
]

# ── Data Generation ───────────────────────────────────────────────────────────
MIN_DATA_ROWS = 20  # Minimum rows the LLM must generate
