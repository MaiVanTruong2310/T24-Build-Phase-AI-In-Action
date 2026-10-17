# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

# Keep the base-image setuptools patch level aligned with requirements.lock.
RUN printf '%s\n' \
    'setuptools==84.0.0 --hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670 --hash=sha256:f4695c21257f0d9b537ec2692c941d02ee143b7cc1276941349a546573b2ef73' \
    > /tmp/runtime-requirements.txt \
    && python -m pip install --no-cache-dir --upgrade --require-hashes --no-deps -r /tmp/runtime-requirements.txt \
    && rm /tmp/runtime-requirements.txt

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code (chown ngay lúc copy)
COPY --chown=appuser:appuser . .

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
