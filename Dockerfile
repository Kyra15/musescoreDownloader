# could not tell you whats going on here
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN patchright install chromium

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "2", "app:app"]