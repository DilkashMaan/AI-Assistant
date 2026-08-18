# 🤖 AI Data Import Agent

An autonomous AI agent that accepts natural language prompts, generates realistic sample data using **Groq LLM**, and imports it into both **Microsoft Excel** and **Google Sheets** — all in one command.

---

## ✨ Features

- 🧠 **Natural language input** — works with any prompt ("employees", "students", "products", etc.)
- 🔄 **Fully dynamic** — no hardcoded data; Groq LLM generates schema + 25 rows every time
- 📄 **CSV generation** — timestamped file saved to `output/`
- 📊 **Excel workbook** — formatted `.xlsx` with bold headers, alternating rows, freeze pane, auto-filter
- 🌐 **Google Sheets** — creates a new sheet, uploads data, formats it, returns a shareable URL
- ✅ **Step-by-step reporting** — colored terminal output for each step

---

## 📁 Project Structure

```
AI_Assistant/
├── agent.py              ← Main entry point
├── config.py             ← Configuration
├── credentials.json      ← Google Service Account credentials
├── requirements.txt
├── tools/
│   ├── llm_client.py     ← Groq API (intent parsing + data generation)
│   ├── csv_tool.py       ← CSV file writing
│   ├── excel_tool.py     ← Excel workbook creation & launch
│   ├── sheets_tool.py    ← Google Sheets API upload
│   └── reporter.py       ← Terminal output reporter
└── output/               ← Generated CSV and Excel files (auto-created)
```

---

## ⚙️ Setup

### 1. Install dependencies
```powershell
pip install -r requirements.txt
```

### 2. Set your Groq API key
```powershell
$env:GROQ_API_KEY = "your_groq_api_key_here"
```
Get a free key at [https://console.groq.com](https://console.groq.com)

### 3. Add Google credentials
Place your `credentials.json` service account file in the project root.

---

## 🚀 Usage

### Interactive mode
```powershell
python agent.py
```

### Direct prompt
```powershell
python agent.py "Create a sample employee CSV and import it into Excel and Google Sheets"
python agent.py "Generate student records and upload to Excel and Google Sheets"
python agent.py "Import product inventory data into Excel and Google Sheets"
```

### Debug mode (shows full tracebacks)
```powershell
python agent.py "..." --debug
```

---

## 📋 Example Output

```
╭─────────────────────────────────────────────────╮
│  🤖 AI Data Import Agent                        │
│  Prompt: Create a sample employee CSV...        │
╰─────────────────────────────────────────────────╯

  ✅ Parse prompt        → Entity: 'employee' | Title: 'Employee Records'
  ✅ Generate schema     → 10 columns: Employee ID, Full Name, Department...
  ✅ Generate sample data → 25 rows generated
  ✅ Write CSV file      → employee_records_20240818_150000.csv
  ✅ Create Excel workbook → employee_records_20240818_150000.xlsx
  ✅ Open in Microsoft Excel → Launched Excel with workbook
  ✅ Upload to Google Sheets → 25 rows uploaded

  📄 CSV File:          C:\...\output\employee_records_20240818_150000.csv
  📊 Excel File:        C:\...\output\employee_records_20240818_150000.xlsx
  🌐 Google Sheet URL:  https://docs.google.com/spreadsheets/d/...

╭────────────────────────────────────────╮
│  🎉 All steps completed successfully!  │
╰────────────────────────────────────────╯
```

---

## 🔑 Requirements

| Requirement | Details |
|---|---|
| Python | 3.10+ |
| Groq API key | Free at console.groq.com |
| Google Service Account | With Sheets API + Drive API enabled |
| Microsoft Excel | Must be installed on Windows |
