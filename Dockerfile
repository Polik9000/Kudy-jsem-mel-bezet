FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OB_INSTANCE=/data
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
COPY . .
EXPOSE 8000
# the web pages; the background worker is the same image with: python -m webapp.worker
# (one race from the command line still works: docker run -v "$PWD/data:/data" ob-tracker python run_race.py ...)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--preload", "--worker-class", "gthread", "--workers", "2", "--threads", "4", "--timeout", "900", "webapp.wsgi:app"]
