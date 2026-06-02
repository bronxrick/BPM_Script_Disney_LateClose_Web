FROM python:3.11-slim

WORKDIR /app

# Install system deps for Playwright (Firefox)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install firefox --with-deps

# Copy app source (credentials and token are injected via env vars, not baked in)
COPY app.py disney_scraper.py google_calendar.py config.py delorean_console.py confirmation_modal.py ./
COPY templates/ templates/

EXPOSE 5000

CMD ["python", "app.py"]
