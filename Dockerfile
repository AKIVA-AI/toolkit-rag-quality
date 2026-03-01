FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .
RUN mkdir -p /app/evaluations /app/reports
ENV PYTHONUNBUFFERED=1
CMD ["toolkit-rag", "--help"]
