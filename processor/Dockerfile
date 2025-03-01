FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy the rest of the application
COPY video_processor.py .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run with unbuffered output for immediate logging
CMD ["python3", "video_processor.py"] 