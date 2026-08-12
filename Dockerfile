FROM python:3.14-slim@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid appuser --create-home --no-log-init appuser \
 && install -d -o appuser -g appuser /app

WORKDIR /app

COPY requirements.txt ./

RUN python - <<'PY'
import codecs
from pathlib import Path

p = Path("requirements.txt")
data = p.read_bytes()
if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
    p.write_text(data.decode("utf-16"), encoding="utf-8")
PY

RUN pip install --no-cache-dir -r requirements.txt

ARG APP_VERSION=development
ENV APP_VERSION=${APP_VERSION}

COPY --chown=appuser:appuser . .

USER appuser

CMD ["python", "main.py"]
