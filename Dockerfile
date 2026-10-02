FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ragsentinel/ ./ragsentinel/
COPY configs/ ./configs/
COPY pyproject.toml .

# Install the package
RUN pip install -e .

# Create data directories
RUN mkdir -p data/ledger

# Expose port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "ragsentinel.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
