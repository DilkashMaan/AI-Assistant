

## 📁 Project Structure

```
AI_Assistant/
├── agent.py              ← Main orchestrator entry point
├── config.py             ← Configuration loader (reads .env)
├── credentials.json      ← Google Service Account credentials
├── Dockerfile            ← Multi-stage Python 3.12 application container
├── docker-compose.yml    ← Container orchestration (App + PostgreSQL)
├── .dockerignore         ← Docker build context exclusions
├── .gitignore            ← Git exclusions (secrets, output, venv)
├── .env                  ← Environment variable configuration
├── requirements.txt      ← Dependencies (groq, openpyxl, psycopg2, google-api)
├── tools/
│   ├── llm_client.py     ← Groq API (intent parsing & dynamic data gen)
│   ├── csv_tool.py       ← CSV file generator
│   ├── excel_tool.py     ← Excel workbook builder & launcher
│   ├── sheets_tool.py    ← Google Sheets API integration
│   ├── db_tool.py        ← PostgreSQL database logger & JSONB recorder
│   ├── prompt_logger.py  ← Database prompt history logger (prompt_logs table)
│   └── reporter.py       ← Rich terminal status reporter
└── output/               ← Generated CSV & Excel files (mounted volume)
```

---

## Docker & Container Management Commands

### 1. Build and Start Container Stack

Starts the PostgreSQL database and runs the AI agent application:

```bash
docker compose up --build
```

Or run in detached background mode:

```bash
docker compose up -d --build
```

### 2. Run Custom Prompt in Container

Run a specific prompt inside the containerized app:

```bash
docker compose run --rm app "Generate student records and upload to Excel and Google Sheets"
```

### 3. Check Container Status

View running containers and health checks:

```bash
docker compose ps
```

### 4. View Container Logs

View live logs from all containers:

```bash
docker compose logs -f
```

View logs for the AI Agent app only:

```bash
docker compose logs -f app
```

View logs for PostgreSQL database container:

```bash
docker compose logs -f db
```

### 5. Stop Containers

Stop all running containers gracefully:

```bash
docker compose stop
```

### 6. Stop and Remove Containers & Networks

Stop containers and clean up container resources:

```bash
docker compose down
```

To also remove the PostgreSQL persistent data volume:

```bash
docker compose down -v
```

### 7. Inspect Data inside PostgreSQL Container

Connect directly to PostgreSQL inside the `db` container to view logged runs and JSONB records:

```bash
docker exec -it ai_assistant_db psql -U postgres -d ai_assistant_db -c "SELECT id, prompt, entity, row_count, status, executed_at FROM workflow_runs;"
```

View stored JSONB dataset records:

```bash
docker exec -it ai_assistant_db psql -U postgres -d ai_assistant_db -c "SELECT run_id, entity, record_data FROM generated_records LIMIT 5;"
```

---

## Local / Direct Execution (Without Docker)

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure `.env`

Ensure your `.env` file contains your Groq API key and configuration:

```ini

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_assistant_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
ENABLE_DB=true
```

### 3. Run Agent directly

```powershell
python agent.py "Create a sample employee CSV and import it into Excel and Google Sheets"
```

---

##Example Terminal Output

```text
┌────────────────────────── AI AI Data Import Agent ──────────────────────────┐
│ Prompt: Create a sample employee CSV and import it into Excel and Google    │
│ Sheets                                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

  ✅ Parse prompt             → Entity: 'employee' | Title: 'Employee Records'
  ✅ Generate schema          → 10 columns: employee_id, first_name, last_name...
  ✅ Generate sample data     → 25 rows generated
  ✅ Write CSV file           → sample_employee_records_20260818_153614.csv
  ✅ Create Excel workbook    → sample_employee_records_20260818_153614.xlsx
  ✅ Open in Microsoft Excel  → Launched Excel with workbook
  ✅ Upload to Google Sheets  → 25 rows uploaded
  ✅ Log to PostgreSQL DB     → Run ID #1 logged with 25 records in DB

  📄 CSV File:          /app/output/sample_employee_records_20260818_153614.csv
  📊 Excel File:        /app/output/sample_employee_records_20260818_153614.xlsx
  🌐 Google Sheet URL:  https://docs.google.com/spreadsheets/d/1RoO60SH1vKLh1YaVqNvKkAPlvicYX-8xZkwdUGbUiqk/edit

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎉 All steps completed successfully!                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```
