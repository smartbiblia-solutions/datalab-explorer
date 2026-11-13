FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATALAB_INSTANCE=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Frontend assets (static/dist, static/keshif) are committed: no Node toolchain in the image.
COPY app.py ./
COPY studio ./studio
COPY templates ./templates
COPY static ./static
RUN useradd --uid 10001 --no-create-home datalab && mkdir /data && chown datalab /data
USER datalab
VOLUME /data
EXPOSE 5000
# One process: API imports run in a background thread of this process (SQLite, single writer).
CMD ["gunicorn", "--no-control-socket", "--bind=0.0.0.0:5000", "--workers=1", "--threads=4", "--timeout=120", "app:app"]
