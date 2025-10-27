# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy all application code
COPY . .

# Install Python dependencies
RUN uv sync --frozen


# Expose port 8009
EXPOSE 8009

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Run the application using python main.py
CMD ["python", "main.py"]
