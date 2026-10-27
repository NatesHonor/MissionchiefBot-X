FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# The real .env is excluded from the build context so credentials are never
# baked into the image. Supply it at runtime with --env-file or Compose.
COPY . .

RUN mkdir -p /app/logs \
    && chown -R pwuser:pwuser /app

USER pwuser

EXPOSE 8765

CMD ["python", "Main.py"]
