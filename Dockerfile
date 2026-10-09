FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    DATABASE_URL=sqlite:////data/calligraphy.db \
    CALLIGRAPHY_OUTPUT_DIR=/data/outputs \
    CALLIGRAPHY_STYLE_DIR=/data/styles \
    CALLIGRAPHY_KAI_CACHE=/data/kai-geometry.db \
    CALLIGRAPHY_CONTACT_CACHE=/data/contact-geometry.db \
    CALLIGRAPHY_ISOLATE_JOBS=1 \
    CALLIGRAPHY_SECURE_COOKIES=1 \
    CALLIGRAPHY_DEMO_ALL_FONTS=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libcairo2 libffi8 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY deploy/requirements-studio.lock /app/deploy/requirements-studio.lock
RUN pip install --no-cache-dir -r deploy/requirements-studio.lock
COPY pyproject.toml README.md ARPHICPL.TXT ./
COPY calligraphy ./calligraphy
RUN pip install --no-cache-dir --no-deps '.[studio]'
COPY backend ./backend
COPY frontend ./frontend
COPY data/calligraphy_fonts.json data/tangshisanbaishou.json ./data/
COPY data/fonts ./data/fonts
COPY data/licenses ./data/licenses
COPY deploy/start.sh ./deploy/start.sh
COPY deploy/check_fonts.py deploy/font_assets.json deploy/prepare_samples.py ./deploy/
RUN mkdir -p /data
EXPOSE 8080
CMD ["sh", "deploy/start.sh"]
