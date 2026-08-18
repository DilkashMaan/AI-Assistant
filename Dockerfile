# Multi-stage Dockerfile for AI Data Import Agent
FROM python:3.12-slim as base

# Set working directory & environment variables
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1

# Install system build dependencies (required for psycopg2 & C libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy & install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and credentials
COPY . .

# Ensure output directory exists
RUN mkdir -p /app/output

# Default command to run the agent
ENTRYPOINT ["python", "agent.py"]
CMD ["Create a sample employee CSV and import it into Excel and Google Sheets"]
