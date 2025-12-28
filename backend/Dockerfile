FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy everything into a specific 'backend' folder inside the container
# This exactly matches the 'from backend.app' imports in your code
WORKDIR /app
COPY . ./backend/

# Ensure the backend folder is treated as a Python package
RUN touch ./backend/__init__.py

# Set PYTHONPATH to the root so 'backend' is discoverable
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check (matches the nested structure)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application using the full package path
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
