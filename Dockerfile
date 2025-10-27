# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl libpq-dev gcc make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen

COPY . .

# Expose port 8009
EXPOSE 8009

# Run the application using python main.py
CMD ["sh", "-c", "uv run python main.py"]