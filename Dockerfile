FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

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
