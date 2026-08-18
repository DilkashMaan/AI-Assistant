"""
tools/sheets_tool.py - Google Sheets integration using the Sheets & Drive APIs.

Strategy: Creates a new Google Spreadsheet OR writes into an existing one.
If GOOGLE_SHEET_ID is set in config, writes to that sheet.
Otherwise, tries to create a new one via the Sheets API.
"""

from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config


# ── Auth ───────────────────────────────────────────────────────────────────────

def _get_services():
    """Build and return (sheets_service, drive_service) authenticated clients."""
    creds = service_account.Credentials.from_service_account_file(
        str(config.GOOGLE_CREDENTIALS_FILE),
        scopes=config.GOOGLE_SCOPES,
    )
    sheets_svc = build("sheets", "v4", credentials=creds)
    drive_svc  = build("drive",  "v3", credentials=creds)
    return sheets_svc, drive_svc


# ── Public API ─────────────────────────────────────────────────────────────────

def create_and_populate(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    share_with_email: Optional[str] = None,
) -> str:
    """
    Create a new Google Spreadsheet and write all data into it,
    OR write into an existing sheet if config.GOOGLE_SHEET_ID is set.

    Returns the URL of the spreadsheet.
    """
    sheets_svc, drive_svc = _get_services()

    # ── Use existing sheet if configured ────────────────────────────────────
    if config.GOOGLE_SHEET_ID:
        return _populate_existing_sheet(sheets_svc, config.GOOGLE_SHEET_ID, title, headers, rows)

    # ── Otherwise try to create a new spreadsheet ────────────────────────────
    try:
        spreadsheet = (
            sheets_svc.spreadsheets()
            .create(
                body={
                    "properties": {"title": title},
                    "sheets": [{"properties": {"title": "Data"}}],
                }
            )
            .execute()
        )
        sheet_id     = spreadsheet["spreadsheetId"]
        sheet_tab_id = spreadsheet["sheets"][0]["properties"]["sheetId"]
        sheet_url    = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    except HttpError as e:
        msg = str(e)
        if "storageQuotaExceeded" in msg or "quota" in msg.lower():
            raise RuntimeError(
                "Google Drive storage quota exceeded for the service account.\n"
                "Fix options:\n"
                "  1. Free up space at https://drive.google.com (logged in as the service account)\n"
                "  2. Set GOOGLE_SHEET_ID in config.py to an existing Sheet ID you've shared "
                "with the service account (dilkash@gen-lang-client-0065720801.iam.gserviceaccount.com) "
                "as Editor."
            ) from e
        raise

    # ── Write all data ────────────────────────────────────────────────────────
    _write_data(sheets_svc, sheet_id, sheet_tab_id, headers, rows)

    # ── Make publicly viewable ────────────────────────────────────────────────
    _make_public(drive_svc, sheet_id, share_with_email)

    return sheet_url


def _populate_existing_sheet(
    sheets_svc,
    sheet_id: str,
    title: str,
    headers: list[str],
    rows: list[list[str]],
) -> str:
    """Write data into an existing spreadsheet (clears first, then writes)."""
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"

    # Get sheet tab metadata
    meta = sheets_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = meta.get("sheets", [])
    if not sheets:
        raise RuntimeError(f"No sheets found in spreadsheet {sheet_id}")

    # Add a new tab named after the title (or reuse Sheet1)
    tab_title = title[:31]
    existing_titles = [s["properties"]["title"] for s in sheets]

    if tab_title not in existing_titles:
        # Add a new sheet tab
        resp = sheets_svc.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_title}}}]},
        ).execute()
        sheet_tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    else:
        # Use existing tab, clear it first
        sheet_tab_id = next(
            s["properties"]["sheetId"]
            for s in sheets
            if s["properties"]["title"] == tab_title
        )
        sheets_svc.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=f"'{tab_title}'!A1:ZZ",
        ).execute()

    # Write data into this tab
    all_values = [headers] + rows
    sheets_svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"'{tab_title}'!A1",
        valueInputOption="RAW",
        body={"values": all_values},
    ).execute()

    # Format
    _format_sheet(sheets_svc, sheet_id, sheet_tab_id, len(headers), len(all_values))

    return sheet_url


def _write_data(sheets_svc, sheet_id: str, sheet_tab_id: int,
                headers: list[str], rows: list[list[str]]) -> None:
    """Write headers + rows to Data tab and apply formatting."""
    all_values = [headers] + rows
    sheets_svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Data!A1",
        valueInputOption="RAW",
        body={"values": all_values},
    ).execute()
    _format_sheet(sheets_svc, sheet_id, sheet_tab_id, len(headers), len(all_values))


def _format_sheet(sheets_svc, sheet_id: str, sheet_tab_id: int,
                  num_cols: int, total_rows: int) -> None:
    """Apply bold header, freeze row, auto-resize, and basic filter."""
    sheets_svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [
            # Bold + navy header
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_tab_id,
                        "startRowIndex": 0, "endRowIndex": 1,
                        "startColumnIndex": 0, "endColumnIndex": num_cols,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.180, "green": 0.251, "blue": 0.341},
                            "textFormat": {
                                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                                "bold": True, "fontSize": 11,
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment":   "MIDDLE",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
                }
            },
            # Auto-resize columns
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": sheet_tab_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0, "endIndex": num_cols,
                    }
                }
            },
            # Freeze header row
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_tab_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            # Basic filter
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_tab_id,
                            "startRowIndex": 0, "endRowIndex": total_rows,
                            "startColumnIndex": 0, "endColumnIndex": num_cols,
                        }
                    }
                }
            },
        ]},
    ).execute()


def _make_public(drive_svc, sheet_id: str, share_with_email: Optional[str] = None) -> None:
    """Make the sheet publicly viewable and optionally share with an email."""
    try:
        drive_svc.permissions().create(
            fileId=sheet_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
    except HttpError:
        pass  # Non-fatal

    if share_with_email:
        try:
            drive_svc.permissions().create(
                fileId=sheet_id,
                body={"type": "user", "role": "writer", "emailAddress": share_with_email},
                sendNotificationEmail=False,
            ).execute()
        except HttpError:
            pass
