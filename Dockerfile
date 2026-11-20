FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MDTECH_HOST="0.0.0.0"
ENV MDTECH_PORT=8765

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure instance directory exists for persistent SQLite database & keys
RUN mkdir -p /app/instance

EXPOSE 8765

VOLUME ["/app/instance"]

CMD ["python", "run.py"]
