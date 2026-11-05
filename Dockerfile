FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Root bo'lmagan foydalanuvchi; data/ — SQLite fayli uchun
RUN useradd --create-home --uid 1000 bot \
    && mkdir -p /app/data \
    && chown -R bot:bot /app/data
USER bot

# main.py avval Alembic migratsiyalarini bajaradi, so'ng polling'ni boshlaydi
CMD ["python", "main.py"]
