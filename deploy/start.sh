#!/bin/sh
set -eu
mkdir -p /data/styles /data/outputs/previews /data/outputs/videos
python deploy/check_fonts.py
python -m deploy.prepare_samples
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port "${PORT:-8080}" \
    --workers 1 --proxy-headers --timeout-graceful-shutdown 20
