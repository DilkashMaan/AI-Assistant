"""
tools/db_tool.py - PostgreSQL integration for logging workflow runs and storing generated records.

Handles schema initialization, execution logging, and data persistence.
Fails gracefully if the database is offline or not configured.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

import config

logger = logging.getLogger("db_tool")
_DB_AVAILABLE: Optional[bool] = None


def get_connection():
    """Establish a connection to the PostgreSQL database with fallback and status caching."""
    global _DB_AVAILABLE
    if not config.ENABLE_DB or _DB_AVAILABLE is False:
        return None

    hosts_to_try = [config.DB_HOST]
    if config.DB_HOST == "db":
        hosts_to_try.append("localhost")

    for host in hosts_to_try:
        try:
            conn = psycopg2.connect(
                host=host,
                port=config.DB_PORT,
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASS,
                connect_timeout=2,
            )
            _DB_AVAILABLE = True
            return conn
        except Exception:
            continue

    if _DB_AVAILABLE is None:
        logger.debug("PostgreSQL database is offline/unreachable. DB persistence skipped.")
        _DB_AVAILABLE = False
    return None


def init_db() -> bool:
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn:
            with conn.cursor() as cur:
                # Table 1: Workflow execution logs
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_runs (
                        id SERIAL PRIMARY KEY,
                        prompt TEXT NOT NULL,
                        entity VARCHAR(100),
                        title VARCHAR(255),
                        csv_path TEXT,
                        excel_path TEXT,
                        google_sheets_url TEXT,
                        row_count INT DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'SUCCESS',
                        executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS generated_records (
                        id SERIAL PRIMARY KEY,
                        run_id INT REFERENCES workflow_runs(id) ON DELETE CASCADE,
                        entity VARCHAR(100),
                        record_data JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS prompt_logs (
                        id SERIAL PRIMARY KEY,
                        prompt TEXT NOT NULL,
                        given_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"Failed to initialize database tables: {e}")
        if conn:
            conn.close()
        return False


def log_prompt(prompt: str) -> Optional[int]:
    conn = get_connection()
    if not conn:
        return None

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO prompt_logs (prompt) VALUES (%s) RETURNING id;",
                    (prompt,),
                )
                prompt_id = cur.fetchone()[0]
        conn.close()
        return prompt_id
    except Exception as e:
        logger.warning(f"Failed to log prompt to PostgreSQL: {e}")
        if conn:
            conn.close()
        return None


def log_workflow_run(
    prompt: str,
    entity: str,
    title: str,
    csv_path: Optional[Path],
    excel_path: Optional[Path],
    google_sheets_url: Optional[str],
    data: List[Dict[str, Any]],
    status: str = "SUCCESS",
) -> Optional[int]:
    conn = get_connection()
    if not conn:
        return None

    run_id = None
    try:
        with conn:
            with conn.cursor() as cur:
                # Insert workflow run entry
                cur.execute(
                    """
                    INSERT INTO workflow_runs (
                        prompt, entity, title, csv_path, excel_path, google_sheets_url, row_count, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        prompt,
                        entity,
                        title,
                        str(csv_path) if csv_path else None,
                        str(excel_path) if excel_path else None,
                        google_sheets_url,
                        len(data),
                        status,
                    ),
                )
                run_id = cur.fetchone()[0]

                # Insert generated records into JSONB table
                if data and run_id:
                    record_tuples = [
                        (run_id, entity, json.dumps(row)) for row in data
                    ]
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO generated_records (run_id, entity, record_data)
                        VALUES %s;
                        """,
                        record_tuples,
                        template="(%s, %s, %s::jsonb)",
                    )

        conn.close()
        return run_id
    except Exception as e:
        logger.warning(f"Failed to log workflow run to PostgreSQL: {e}")
        if conn:
            conn.close()
        return None
