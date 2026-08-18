

import csv
from datetime import datetime
from pathlib import Path

import config


def write_csv(data: list[dict], filename_base: str) -> Path:
    
    if not data:
        raise ValueError("Cannot write CSV: data list is empty.")

    # Build a safe, timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_base = "".join(c if c.isalnum() or c == "_" else "_" for c in filename_base)
    csv_path = config.OUTPUT_DIR / f"{safe_base}_{timestamp}.csv"

    columns = list(data[0].keys())

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    return csv_path


def read_csv(csv_path: Path) -> tuple[list[str], list[list[str]]]:
    
    headers: list[str] = []
    rows: list[list[str]] = []

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
            else:
                rows.append(row)

    return headers, rows
