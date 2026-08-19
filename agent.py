

import sys
import traceback
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from tools.reporter import Reporter, StepResult
from tools import llm_client, csv_tool, excel_tool, sheets_tool, db_tool, prompt_logger

console = Console()


# ── Step wrappers ──────────────────────────────────────────────────────────────

def step_save_prompt(reporter: Reporter, prompt: str) -> Optional[int]:
    """Step 0: Save user prompt with timestamp to PostgreSQL DB."""
    reporter.step_start("Log prompt to PostgreSQL DB")
    try:
        prompt_id = prompt_logger.save_prompt(prompt)
        if prompt_id:
            reporter.step_done(StepResult(
                step="Log prompt to DB",
                success=True,
                detail=f"Prompt ID #{prompt_id} logged in DB",
            ))
        else:
            reporter.step_done(StepResult(
                step="Log prompt to DB",
                success=True,
                detail="Database disabled/offline (skipped)",
            ))
        return prompt_id
    except Exception as e:
        reporter.step_done(StepResult("Log prompt to DB", False, str(e)))
        return None


def step_parse_prompt(reporter: Reporter, prompt: str) -> dict:
    """Step 1: Parse the user's natural language prompt via LLM."""
    reporter.step_start("Parse prompt (LLM intent detection)")
    try:
        intent = llm_client.parse_prompt(prompt)
        reporter.step_done(StepResult(
            step="Parse prompt",
            success=True,
            detail=f"Entity: '{intent.get('entity')}' | Title: '{intent.get('title')}'",
        ))
        return intent
    except Exception as e:
        reporter.step_done(StepResult("Parse prompt", False, str(e)))
        raise


def step_generate_schema(reporter: Reporter, entity: str) -> list[str]:
    """Step 2: Ask the LLM what columns this entity type should have."""
    reporter.step_start("Generate data schema (LLM)")
    try:
        schema = llm_client.generate_schema(entity)
        columns = schema.get("columns", [])
        if not columns:
            raise ValueError("LLM returned empty columns list.")
        reporter.step_done(StepResult(
            step="Generate schema",
            success=True,
            detail=f"{len(columns)} columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}",
        ))
        return columns
    except Exception as e:
        reporter.step_done(StepResult("Generate schema", False, str(e)))
        raise


def step_generate_data(reporter: Reporter, entity: str, columns: list[str]) -> list[dict]:
    """Step 3: Generate 25 rows of realistic sample data via LLM."""
    reporter.step_start("Generate sample data (LLM)")
    try:
        data = llm_client.generate_data(entity, columns, num_rows=25)
        reporter.step_done(StepResult(
            step="Generate sample data",
            success=True,
            detail=f"{len(data)} rows generated",
        ))
        return data
    except Exception as e:
        reporter.step_done(StepResult("Generate sample data", False, str(e)))
        raise


def step_write_csv(reporter: Reporter, data: list[dict], filename_base: str):
    """Step 4: Write data to a CSV file."""
    reporter.step_start("Write CSV file")
    try:
        csv_path = csv_tool.write_csv(data, filename_base)
        reporter.step_done(StepResult(
            step="Write CSV file",
            success=True,
            detail=str(csv_path.name),
            extra={"📄 CSV File": str(csv_path)},
        ))
        return csv_path
    except Exception as e:
        reporter.step_done(StepResult("Write CSV file", False, str(e)))
        raise


def step_create_excel(reporter: Reporter, headers: list[str], rows: list[list[str]], csv_path, sheet_title: str):
    """Step 5: Create formatted Excel workbook from CSV data."""
    reporter.step_start("Create Excel workbook (.xlsx)")
    try:
        xlsx_path = excel_tool.create_workbook(headers, rows, csv_path, sheet_title)
        reporter.step_done(StepResult(
            step="Create Excel workbook",
            success=True,
            detail=xlsx_path.name,
            extra={"📊 Excel File": str(xlsx_path)},
        ))
        return xlsx_path
    except Exception as e:
        reporter.step_done(StepResult("Create Excel workbook", False, str(e)))
        raise


def step_open_excel(reporter: Reporter, xlsx_path):
    """Step 6: Open the workbook in Microsoft Excel (or save in headless/Linux OS)."""
    reporter.step_start("Open in Microsoft Excel")
    try:
        msg = excel_tool.open_in_excel(xlsx_path)
        reporter.step_done(StepResult(
            step="Open in Microsoft Excel",
            success=True,
            detail=msg,
        ))
    except Exception as e:
        reporter.step_done(StepResult("Open in Microsoft Excel", False, str(e)))
        # Non-fatal: Excel may not be installed but file is still saved


def step_upload_sheets(reporter: Reporter, title: str, headers: list[str], rows: list[list[str]]):
    """Step 7: Create Google Sheet and upload all data."""
    reporter.step_start("Upload to Google Sheets")
    try:
        url = sheets_tool.create_and_populate(title, headers, rows)
        reporter.step_done(StepResult(
            step="Upload to Google Sheets",
            success=True,
            detail=f"{len(rows)} rows uploaded",
            extra={"🌐 Google Sheet URL": url},
        ))
        return url
    except Exception as e:
        reporter.step_done(StepResult("Upload to Google Sheets", False, _friendly_sheets_error(e)))
        # Non-fatal: CSV and Excel steps already succeeded


def _friendly_sheets_error(exc: Exception) -> str:
    """Return a human-readable error message for common Google Sheets errors."""
    msg = str(exc)
    if "403" in msg or "does not have permission" in msg.lower():
        return (
            "403 Permission Denied. Enable the APIs at:\n"
            "  Sheets: https://console.cloud.google.com/apis/library/sheets.googleapis.com"
            "?project=gen-lang-client-0065720801\n"
            "  Drive:  https://console.cloud.google.com/apis/library/drive.googleapis.com"
            "?project=gen-lang-client-0065720801"
        )
    if "400" in msg:
        return f"400 Bad Request: {msg[:200]}"
    return msg[:300]


def step_log_postgres(
    reporter: Reporter,
    prompt: str,
    entity: str,
    title: str,
    csv_path,
    xlsx_path,
    sheets_url,
    data: list[dict],
):
    """Step 8: Log workflow run and generated records into PostgreSQL database."""
    reporter.step_start("Log run to PostgreSQL Database")
    try:
        run_id = db_tool.log_workflow_run(
            prompt=prompt,
            entity=entity,
            title=title,
            csv_path=csv_path,
            excel_path=xlsx_path,
            google_sheets_url=sheets_url,
            data=data,
        )
        if run_id:
            reporter.step_done(
                StepResult(
                    step="Log to PostgreSQL Database",
                    success=True,
                    detail=f"Run ID #{run_id} logged with {len(data)} records in DB",
                )
            )
        else:
            reporter.step_done(
                StepResult(
                    step="Log to PostgreSQL Database",
                    success=True,
                    detail="Database disabled/offline (skipped)",
                )
            )
    except Exception as e:
        reporter.step_done(StepResult("Log to PostgreSQL Database", False, str(e)))


# ── Main orchestrator ──────────────────────────────────────────────────────────

def run_agent(prompt: str) -> None:
    """Execute the full agent workflow for the given natural language prompt."""
    reporter = Reporter(title="AI Data Import Agent")
    reporter.start(prompt)

    # Initialize PostgreSQL schema if DB connection is active
    db_tool.init_db()

    # Log user prompt with timestamp ("when we give")
    step_save_prompt(reporter, prompt)

    entity = "record"
    sheet_title = "Sample Data"
    csv_path = None
    xlsx_path = None
    sheets_url = None
    data = []

    try:
        # ── Step 1: Understand the prompt ──────────────────────────────────
        intent = step_parse_prompt(reporter, prompt)
        entity        = intent.get("entity", "record")
        sheet_title   = intent.get("title", "Sample Data")
        filename_base = intent.get("filename", "sample_data")

        # ── Step 2: Define columns ─────────────────────────────────────────
        columns = step_generate_schema(reporter, entity)

        # ── Step 3: Generate data rows ─────────────────────────────────────
        data = step_generate_data(reporter, entity, columns)

        # ── Step 4: Write CSV ──────────────────────────────────────────────
        csv_path = step_write_csv(reporter, data, filename_base)

        # Read back as plain rows for Excel & Sheets
        headers, rows = csv_tool.read_csv(csv_path)

        # ── Step 5: Create Excel workbook ──────────────────────────────────
        xlsx_path = step_create_excel(reporter, headers, rows, csv_path, sheet_title)

        # ── Step 6: Open Excel ─────────────────────────────────────────────
        step_open_excel(reporter, xlsx_path)

        # ── Step 7: Google Sheets upload (non-fatal) ───────────────────────
        sheets_url = step_upload_sheets(reporter, sheet_title, headers, rows)

        # ── Step 8: Log to PostgreSQL Database (non-fatal) ──────────────────
        step_log_postgres(reporter, prompt, entity, sheet_title, csv_path, xlsx_path, sheets_url, data)

    except Exception as exc:
        console.print(f"\n[bold red]Fatal error:[/bold red] {exc}")
        if "--debug" in sys.argv:
            traceback.print_exc()

    finally:
        reporter.summary()



# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Accept prompt from CLI args or prompt interactively
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        user_prompt = " ".join(args)
    else:
        console.print(
            "\n[bold magenta]🤖 AI Data Import Agent[/bold magenta]\n"
            "  Generates a CSV with sample data, imports it into Excel,\n"
            "  and uploads it to a new Google Sheet.\n"
        )
        user_prompt = Prompt.ask(
            "[bold cyan]Enter your prompt[/bold cyan]",
            default="Create a sample employee CSV and import it into Excel and Google Sheets",
        )

    run_agent(user_prompt)
