# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS node

FROM python:3.12-slim-bookworm AS build
WORKDIR /app
# The frontend build verifies its Keshif patch ledger with Python.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
COPY requirements.lock ./
RUN --mount=type=secret,id=python_ca \
    python -m venv /opt/venv && \
    if [ -f /run/secrets/python_ca ]; then export PIP_CERT=/run/secrets/python_ca; fi && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.lock && \
    /opt/venv/bin/pip check
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi && \
    npm ci --no-audit --no-fund
COPY tsconfig.json ./
COPY frontend ./frontend
COPY scripts/build.mjs scripts/verify-vendor.py ./scripts/
COPY vendor ./vendor
COPY static/studio.css static/demo.csv ./static/
RUN npm run typecheck && npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATALAB_INSTANCE=/data
WORKDIR /app
RUN groupadd --gid 10001 datalab && \
    useradd --uid 10001 --gid datalab --no-create-home datalab && \
    mkdir /data && chown datalab:datalab /data
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/static ./static
COPY --from=build /app/vendor ./vendor
COPY studio ./studio
COPY templates ./templates
COPY app.py ./
# Checkouts can use owner-only permissions; the runtime user still needs read access.
RUN chmod -R a+rX /app /opt/venv
USER datalab
EXPOSE 5000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=3)); assert r['status']=='ok' and r['schema']==2 and r['build']"
CMD ["gunicorn", "--no-control-socket", "--bind=0.0.0.0:5000", "--workers=1", "--timeout=120", "--access-logfile=-", "--error-logfile=-", "app:app"]
