FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config.yaml ./config.yaml

RUN mkdir -p logs

RUN useradd -m -u 1000 forex && chown -R forex:forex /app
USER forex

CMD ["python", "-m", "src.cli.main", "run"]
