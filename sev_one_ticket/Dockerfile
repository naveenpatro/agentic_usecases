FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# chromium for pyppeteer
RUN apt-get update && apt-get install -y \
    wget ca-certificates gnupg2 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libx11-xcb1 libxcomposite1 libxrandr2 libxdamage1 libxfixes3 libxkbcommon0 libgbm1 libasound2 xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
