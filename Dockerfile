FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AGENT_MODE=demo TRAINING_DB=/app/data/training.db
WORKDIR /app
COPY requirements-runtime.txt ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-runtime.txt \
    && groupadd --gid 10001 agentx \
    && useradd --uid 10001 --gid agentx --no-create-home agentx \
    && mkdir /app/data && chown agentx:agentx /app/data
COPY src/ ./src/
COPY agents/system_prompts/ ./agents/system_prompts/
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
