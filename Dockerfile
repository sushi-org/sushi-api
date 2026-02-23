FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy uv.lock and pyproject.toml first for better caching
COPY uv.lock pyproject.toml ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy the application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Expose port (Cloud Run expects 8080)
EXPOSE 8080

# Run the FastAPI application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]