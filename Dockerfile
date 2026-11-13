FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATALAB_INSTANCE=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./
COPY datalab ./datalab
COPY templates ./templates
COPY static ./static
RUN useradd --uid 10001 --no-create-home datalab && mkdir /data && chown datalab /data
USER datalab
VOLUME /data
EXPOSE 5000
# One process: SQLite and the JSON data files have a single writer.
CMD ["gunicorn", "--no-control-socket", "--bind=0.0.0.0:5000", "--workers=1", "--threads=4", "--timeout=120", "app:app"]
