FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aider-chat && \
    apt-get update && \
    apt-get install -y git

COPY . .

CMD ["python", "app.py"]
