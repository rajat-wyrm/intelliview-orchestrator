FROM python:3.11-slim-bullseye

WORKDIR /app
ENV PYTHONPATH=/app
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "cv_service.app:app", "--host", "0.0.0.0", "--port", "8001"]