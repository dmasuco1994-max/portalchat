FROM python:3.11-slim

# Prevent Python from writing .pyc files and force unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python deps first for better Docker layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy application code
COPY app ./app

EXPOSE 8000

# Hot reload enabled — the volume mount in docker-compose syncs host code into /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
