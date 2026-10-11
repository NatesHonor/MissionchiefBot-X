FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

RUN useradd --create-home --uid 10001 missionchief \
    && mkdir -p /app/logs \
    && chown -R missionchief:missionchief /app /ms-playwright
USER missionchief

CMD ["python", "Main.py"]
