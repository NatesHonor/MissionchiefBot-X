FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# The real config.ini is excluded from the build context so credentials are
# never baked into the image. Runtime environment variables can override it.
COPY config.ini.example ./config.ini
COPY . .

RUN mkdir -p /app/logs \
    && chown -R pwuser:pwuser /app

USER pwuser

CMD ["python", "Main.py"]
