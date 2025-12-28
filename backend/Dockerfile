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

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy everything into the root of the container
WORKDIR /app
COPY . .

# Multi-service fix: Create a symlink so that 'import backend.app' works 
# even though we are currently INSIDE the backend folder.
RUN ln -s . backend

# Set PYTHONPATH to the current directory
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
# We use uvicorn app.main:app because Railway expects the app folder to be in the root
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
