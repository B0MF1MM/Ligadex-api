FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg ca-certificates \
    --no-install-recommends

# Instala Chrome 148 (versão fixa para compatibilidade com ChromeDriver)
RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_148.0.7778.178-1_amd64.deb \
    && apt-get install -y ./google-chrome-stable_148.0.7778.178-1_amd64.deb --no-install-recommends \
    && rm google-chrome-stable_148.0.7778.178-1_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/google-chrome

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120", "--workers", "1"]