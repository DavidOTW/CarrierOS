FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CARRIEROS_DB=/data/carrieros.db \
    CARRIEROS_ENV=production

WORKDIR /app
RUN addgroup --system carrieros && adduser --system --ingroup carrieros carrieros \
    && mkdir -p /data /var/lib/clamav \
    && chown -R carrieros:carrieros /data /var/lib/clamav
RUN apt-get update \
    && apt-get install -y --no-install-recommends clamav clamav-freshclam \
    && freshclam --stdout --no-warnings \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=carrieros:carrieros . .

USER carrieros
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health', timeout=3)"
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
