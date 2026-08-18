"""
tools/llm_client.py - Groq LLM wrapper for intent parsing and data generation.

Three responsibilities:
  1. parse_prompt()    -> understand what kind of data the user wants
  2. generate_schema() -> define appropriate columns for that entity type
  3. generate_data()   -> produce 25+ rows of realistic sample data (batched)
"""

import csv as _csv
import io as _io
import json
import re
import sys
from typing import Any

from groq import Groq

import config
from tools.reporter import console


# ── Groq client ────────────────────────────────────────────────────────────────

def _get_client() -> Groq:
    if not config.GROQ_API_KEY:
        console.print(
            "[bold red]ERROR:[/bold red] GROQ_API_KEY environment variable is not set.\n"
            "  Set it with:  $env:GROQ_API_KEY = 'your_key'  (PowerShell)"
        )
        sys.exit(1)
    return Groq(api_key=config.GROQ_API_KEY)


def _chat(client: Groq, system: str, user: str, model: str = None) -> str:
    """Send a chat completion request, trying models in priority order."""
    models_to_try = [model] if model else config.GROQ_MODELS
    errors = []
    for m in models_to_try:
        try:
            # Qwen/thinking models: prepend /no_think to suppress chain-of-thought
            user_msg = f"/no_think\n{user}" if "qwen" in m.lower() else user
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=config.GROQ_TEMPERATURE,
                max_tokens=config.GROQ_MAX_TOKENS,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            errors.append(f"  [{m}] {e}")
            continue
    error_details = "\n".join(errors)
    raise RuntimeError(f"All Groq models failed:\n{error_details}")


def _extract_json(text: str) -> Any:
    """
    Extract the first valid JSON object or array from a string.
    Handles:
     - <think>...</think> reasoning blocks (Qwen/DeepSeek style)
     - markdown code fences
     - /no_think control tokens
    """
    # Strip <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Strip /no_think tokens
    text = re.sub(r"/?no_think", "", text, flags=re.IGNORECASE)
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array or object within the text (non-greedy first)
    for pattern in (r"(\[.*?\])", r"(\{.*?\})"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue

    # Last resort: greedy search
    for pattern in (r"(\[.+\])", r"(\{.+\})"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract valid JSON from LLM response:\n{text[:800]}")


def _clean_csv_output(raw: str) -> str:
    """Remove think blocks, markdown fences, and whitespace from model CSV output."""
    # Strip closed <think>...</think> blocks
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    # Strip unclosed <think> blocks (everything from <think> to the end)
    if "<think>" in raw:
        raw = raw.split("<think>")[0]
    # Strip markdown code fences
    raw = re.sub(r"```[a-z]*", "", raw)
    raw = raw.strip().strip("`").strip()
    return raw


def _parse_csv_rows(raw: str, columns: list[str]) -> list[dict]:
    """Parse raw CSV text into a list of dicts using the given column names."""
    reader = _csv.reader(_io.StringIO(raw))
    rows: list[dict] = []
    
    # Common meta-text markers emitted by thinking/reasoning models
    junk_prefixes = (
        "<think>", "here's", "analyze", "task:", "columns:", "rules:",
        "output", "1.", "2.", "3.", "4.", "5.", "**", "##", "#", "-", "*", ">"
    )

    for row in reader:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        first_cell = row[0].strip()
        first_cell_lower = first_cell.lower()

        # Skip accidental header rows
        if first_cell_lower == columns[0].strip().lower():
            continue

        # Skip meta-text / reasoning lines
        if any(first_cell_lower.startswith(p) for p in junk_prefixes):
            continue

        # Skip lines with markdown bolding or backticks anywhere in the first cell
        if "**" in first_cell or "```" in first_cell or "`" in first_cell:
            continue

        # Valid CSV data row must have at least 2 fields if columns > 1, 
        # or at least a reasonable portion of expected columns
        if len(columns) > 1 and len(row) < 2:
            continue

        # Pad/trim to column count and build dict
        padded = (row + [""] * len(columns))[: len(columns)]
        rows.append(dict(zip(columns, [v.strip() for v in padded])))
    return rows


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_prompt(prompt: str) -> dict:
    """
    Use Groq to understand the user's intent.

    Returns a dict like:
    {
      "entity":      "employee",
      "title":       "Employee Records",
      "filename":    "employee_records",
      "description": "..."
    }
    """
    client = _get_client()
    system = (
        "You are an intent parser for a data-generation agent. "
        "Given a user prompt, extract what kind of data they want generated. "
        "Respond ONLY with valid JSON, no markdown, no explanation."
    )
    user = (
        f"User prompt: \"{prompt}\"\n\n"
        "Return a JSON object with these exact keys:\n"
        "  entity      - the type of data entity (e.g. employee, student, product, patient)\n"
        "  title       - a human-readable title for the spreadsheet (e.g. 'Employee Records')\n"
        "  filename    - a snake_case filename base without extension (e.g. employee_records)\n"
        "  description - one sentence describing the dataset"
    )
    raw = _chat(client, system, user)
    return _extract_json(raw)


def generate_schema(entity: str) -> dict:
    """
    Ask the LLM to define appropriate columns for the given entity type.

    Returns a dict like:
    {
      "columns": ["Employee ID", "Full Name", "Department", ...]
    }
    """
    client = _get_client()
    system = (
        "You are a data schema designer. "
        "Given an entity type, define realistic, professional column names for a spreadsheet. "
        "Respond ONLY with valid JSON."
    )
    user = (
        f"Entity type: {entity}\n\n"
        f"Define 8-12 columns suitable for a {entity} dataset. "
        "Include a primary key / ID column, personal/descriptive fields, and numeric/date fields. "
        "Return JSON: {\"columns\": [\"Col1\", \"Col2\", ...]}"
    )
    raw = _chat(client, system, user)
    return _extract_json(raw)


def generate_data(entity: str, columns: list[str], num_rows: int = 25) -> list[dict]:
    """
    Generate num_rows rows of realistic sample data for the given entity and columns.

    Uses a BATCHED approach: requests BATCH_SIZE rows per LLM call to avoid
    output truncation, then combines all batches. Each small call always completes.

    Returns a list of dicts where each dict maps column_name -> value.
    """
    BATCH_SIZE = 5  # rows per call — small enough to always complete fully

    client = _get_client()
    num_rows = max(num_rows, config.MIN_DATA_ROWS)
    header_line = ",".join(columns)
    first_col = columns[0]  # usually the ID column

    system = (
        "You are a synthetic data generator. "
        "Generate realistic, diverse, and believable sample data in CSV format. "
        "Output ONLY raw CSV data rows — no headers, no markdown, no code fences, no explanation. "
        "Each line is exactly one complete data row. Values containing commas must be double-quoted."
    )

    def _fetch_batch(batch_num: int, count: int, used_ids: list[str]) -> list[dict]:
        """Request one small batch of CSV rows from the LLM."""
        id_hint = (
            f"IDs should start from roughly {batch_num * BATCH_SIZE + 1}."
            if batch_num > 0 else ""
        )
        user = (
            f"Generate exactly {count} CSV data rows for a '{entity}' dataset. "
            f"{id_hint}\n\n"
            f"Columns (in this exact order): {header_line}\n\n"
            f"Rules:\n"
            f"- Output ONLY {count} data rows, one per line\n"
            f"- NO header row, NO blank lines, NO extra text\n"
            f"- Exactly {len(columns)} comma-separated values per row\n"
            f"- Use realistic varied names (different genders and ethnicities)\n"
            f"- Dates in YYYY-MM-DD format\n"
            f"- Numbers as plain integers/decimals (no $ or , inside numbers)\n"
            f"- IDs must be unique (do NOT reuse: "
            f"{', '.join(used_ids[-5:]) if used_ids else 'none yet'})\n"
            f"- Quote any value that contains a comma\n\n"
            f"Output exactly {count} rows now:"
        )
        raw = _chat(client, system, user)
        raw = _clean_csv_output(raw)
        return _parse_csv_rows(raw, columns)

    # ── Collect batches until we have enough rows ──────────────────────────────
    all_data: list[dict] = []
    used_ids: list[str] = []
    batch_num = 0
    max_batches = num_rows * 2  # safety limit

    while len(all_data) < num_rows and batch_num < max_batches:
        needed = min(BATCH_SIZE, num_rows - len(all_data))
        batch = _fetch_batch(batch_num, needed, used_ids)

        for row in batch:
            row_id = str(row.get(first_col, "")).strip()
            if row_id and row_id in used_ids:
                continue  # skip duplicate IDs
            all_data.append(row)
            if row_id:
                used_ids.append(row_id)

        batch_num += 1

    if len(all_data) < config.MIN_DATA_ROWS:
        raise ValueError(
            f"Only collected {len(all_data)} rows after {batch_num} batches "
            f"(minimum {config.MIN_DATA_ROWS} required)."
        )

    return all_data[:num_rows]
