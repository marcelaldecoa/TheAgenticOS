FROM python:3.12-slim AS builder

WORKDIR /build
COPY src/server/ ./
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Agent Governance Runtime"
LABEL org.opencontainers.image.description="DAPR-like governance runtime for AI agents"
LABEL org.opencontainers.image.source="https://github.com/marcelaldecoa/TheAgenticOS"
LABEL org.opencontainers.image.licenses="Apache-2.0"

COPY --from=builder /install /usr/local

# Data directory for SQLite (mount a volume in production)
RUN mkdir -p /data
ENV AGR_DB_PATH=/data/agr.db
ENV AGR_HOST=0.0.0.0
ENV AGR_PORT=8600

EXPOSE 8600

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8600/health').raise_for_status()"

CMD ["agr-server"]
